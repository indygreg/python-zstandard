// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{
        compressor::CCtx,
        exceptions::ZstdError,
        stream::{make_in_buffer_source, InBufferSource},
    },
    pyo3::{prelude::*, types::PyBytes, PyIterProtocol},
    std::sync::Arc,
};

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdCompressorIterator {
    cctx: Arc<CCtx<'static>>,
    source: Box<dyn InBufferSource + Send>,
    write_size: usize,
    finished_output: bool,
}

impl ZstdCompressorIterator {
    pub fn new(
        py: Python,
        cctx: Arc<CCtx<'static>>,
        reader: &PyAny,
        read_size: usize,
        write_size: usize,
    ) -> PyResult<Self> {
        Ok(Self {
            cctx,
            source: make_in_buffer_source(py, reader, read_size)?,
            write_size,
            finished_output: false,
        })
    }
}

#[pyproto]
impl PyIterProtocol for ZstdCompressorIterator {
    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<Self>) -> PyResult<Option<PyObject>> {
        if slf.finished_output {
            return Ok(None);
        }

        let py = unsafe { Python::assume_gil_acquired() };

        let mut dest_buffer: Vec<u8> = Vec::with_capacity(slf.write_size);
        let mut out_buffer = zstd_sys::ZSTD_outBuffer {
            dst: dest_buffer.as_mut_ptr() as *mut _,
            size: dest_buffer.capacity(),
            pos: 0,
        };

        // Feed data into the compressor until there is output data.
        while let Some(mut in_buffer) = slf.source.input_buffer(py)? {
            let zresult = unsafe {
                zstd_sys::ZSTD_compressStream2(
                    slf.cctx.cctx(),
                    &mut out_buffer as *mut _,
                    &mut in_buffer as *mut _,
                    zstd_sys::ZSTD_EndDirective::ZSTD_e_continue,
                )
            };
            if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
                return Err(ZstdError::new_err(format!(
                    "zstd compress error: {}",
                    zstd_safe::get_error_name(zresult)
                )));
            }

            slf.source.record_bytes_read(in_buffer.pos);

            // Emit compressed data, if available.
            if out_buffer.pos != 0 {
                unsafe {
                    dest_buffer.set_len(out_buffer.pos);
                }
                // TODO avoid buffer copy
                let chunk = PyBytes::new(py, &dest_buffer);

                return Ok(Some(chunk.into_py(py)));
            }

            // Else read another chunk in hopes of producing output data.
            continue;
        }

        // Input data is exhausted. End the stream and emit what remains.

        let mut in_buffer = zstd_sys::ZSTD_inBuffer {
            src: std::ptr::null_mut(),
            size: 0,
            pos: 0,
        };

        let zresult = unsafe {
            zstd_sys::ZSTD_compressStream2(
                slf.cctx.cctx(),
                &mut out_buffer as *mut _,
                &mut in_buffer as *mut _,
                zstd_sys::ZSTD_EndDirective::ZSTD_e_end,
            )
        };
        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            return Err(ZstdError::new_err(format!(
                "error ending compression stream: {}",
                zstd_safe::get_error_name(zresult)
            )));
        }

        if zresult == 0 {
            slf.finished_output = true;
        }

        if out_buffer.pos != 0 {
            unsafe {
                dest_buffer.set_len(out_buffer.pos);
            }

            // TODO avoid buffer copy.
            let chunk = PyBytes::new(py, &dest_buffer);

            return Ok(Some(chunk.into_py(py)));
        }

        Ok(None)
    }
}
