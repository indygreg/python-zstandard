// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::compressor::CCtx;
use crate::constants::{COMPRESSOBJ_FLUSH_BLOCK, COMPRESSOBJ_FLUSH_FINISH};
use crate::ZstdError;
use cpython::buffer::PyBuffer;
use cpython::exc::ValueError;
use cpython::{py_class, PyBytes, PyErr, PyObject, PyResult, Python};
use std::cell::RefCell;
use std::sync::Arc;

pub struct CompressionObjState<'cctx> {
    cctx: Arc<CCtx<'cctx>>,
    finished: bool,
}

py_class!(pub class ZstdCompressionObj |py| {
    data state: RefCell<CompressionObjState<'static>>;

    def compress(&self, data: PyObject) -> PyResult<PyBytes> {
        self.compress_impl(py, data)
    }

    def flush(&self, flush_mode: Option<i32> = None) -> PyResult<PyBytes> {
        self.flush_impl(py, flush_mode)
    }
});

impl ZstdCompressionObj {
    pub fn new(py: Python, cctx: Arc<CCtx<'static>>) -> PyResult<ZstdCompressionObj> {
        let state = CompressionObjState {
            cctx,
            finished: false,
        };

        Ok(ZstdCompressionObj::create_instance(
            py,
            RefCell::new(state),
        )?)
    }

    fn compress_impl(&self, py: Python, data: PyObject) -> PyResult<PyBytes> {
        let state: std::cell::Ref<CompressionObjState> = self.state(py).borrow();

        if state.finished {
            return Err(ZstdError::from_message(
                py,
                "cannot call compress() after compressor finished",
            ));
        }

        let buffer = PyBuffer::get(py, &data)?;

        let mut source = unsafe {
            std::slice::from_raw_parts::<u8>(buffer.buf_ptr() as *const _, buffer.len_bytes())
        };

        // TODO consider collecting chunks and joining
        // TODO try to use zero copy into return value.
        let mut compressed = Vec::new();
        let write_size = zstd_safe::cstream_out_size();

        let cctx = &state.cctx;
        while !source.is_empty() {
            let result = py
                .allow_threads(|| {
                    cctx.compress_chunk(
                        source,
                        zstd_sys::ZSTD_EndDirective::ZSTD_e_continue,
                        write_size,
                    )
                })
                .or_else(|msg| {
                    Err(ZstdError::from_message(
                        py,
                        format!("zstd compress error: {}", msg).as_ref(),
                    ))
                })?;

            compressed.extend(result.0);
            source = result.1;
        }

        Ok(PyBytes::new(py, &compressed))
    }

    fn flush_impl(&self, py: Python, flush_mode: Option<i32>) -> PyResult<PyBytes> {
        let mut state: std::cell::RefMut<CompressionObjState> = self.state(py).borrow_mut();

        let flush_mode = if let Some(flush_mode) = flush_mode {
            match flush_mode {
                COMPRESSOBJ_FLUSH_FINISH => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_end),
                COMPRESSOBJ_FLUSH_BLOCK => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_flush),
                _ => Err(PyErr::new::<ValueError, _>(py, "flush mode not recognized")),
            }
        } else {
            Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_end)
        }?;

        if state.finished {
            return Err(ZstdError::from_message(
                py,
                "compressor object already finished",
            ));
        }

        if flush_mode == zstd_sys::ZSTD_EndDirective::ZSTD_e_end {
            state.finished = true;
        }

        let write_size = zstd_safe::cstream_out_size();
        let cctx = &state.cctx;

        // TODO avoid extra buffer copy.
        let mut result = Vec::new();

        loop {
            let (chunk, _, call_again) = py
                .allow_threads(|| cctx.compress_chunk(&[], flush_mode, write_size))
                .or_else(|msg| {
                    Err(ZstdError::from_message(
                        py,
                        format!("error ending compression stream: {}", msg).as_ref(),
                    ))
                })?;

            result.extend(&chunk);

            if !call_again {
                return Ok(PyBytes::new(py, &result));
            }
        }
    }
}
