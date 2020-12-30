// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{
        compressor::CCtx,
        constants::{COMPRESSOBJ_FLUSH_BLOCK, COMPRESSOBJ_FLUSH_FINISH},
        ZstdError,
    },
    pyo3::{buffer::PyBuffer, exceptions::PyValueError, prelude::*, types::PyBytes},
    std::{cell::RefCell, sync::Arc},
};

pub struct CompressionObjState<'cctx> {
    cctx: Arc<CCtx<'cctx>>,
    finished: bool,
}

#[pyclass]
pub struct ZstdCompressionObj {
    state: RefCell<CompressionObjState<'static>>,
}

impl ZstdCompressionObj {
    pub fn new(cctx: Arc<CCtx<'static>>) -> PyResult<Self> {
        let state = CompressionObjState {
            cctx,
            finished: false,
        };

        Ok(ZstdCompressionObj {
            state: RefCell::new(state),
        })
    }
}

#[pymethods]
impl ZstdCompressionObj {
    fn compress<'p>(&self, py: Python<'p>, buffer: PyBuffer<u8>) -> PyResult<&'p PyBytes> {
        let state = self.state.borrow();

        if state.finished {
            return Err(ZstdError::new_err(
                "cannot call compress() after compressor finished",
            ));
        }

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
                .or_else(|msg| Err(ZstdError::new_err(format!("zstd compress error: {}", msg))))?;

            compressed.extend(result.0);
            source = result.1;
        }

        Ok(PyBytes::new(py, &compressed))
    }

    fn flush<'p>(&mut self, py: Python<'p>, flush_mode: Option<i32>) -> PyResult<&'p PyBytes> {
        let mut state = self.state.borrow_mut();

        let flush_mode = if let Some(flush_mode) = flush_mode {
            match flush_mode {
                COMPRESSOBJ_FLUSH_FINISH => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_end),
                COMPRESSOBJ_FLUSH_BLOCK => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_flush),
                _ => Err(PyValueError::new_err("flush mode not recognized")),
            }
        } else {
            Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_end)
        }?;

        if state.finished {
            return Err(ZstdError::new_err("compressor object already finished"));
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
                    Err(ZstdError::new_err(format!(
                        "error ending compression stream: {}",
                        msg
                    )))
                })?;

            result.extend(&chunk);

            if !call_again {
                return Ok(PyBytes::new(py, &result));
            }
        }
    }
}
