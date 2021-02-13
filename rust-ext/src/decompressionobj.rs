// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{decompressor::DCtx, exceptions::ZstdError},
    pyo3::{
        buffer::PyBuffer,
        prelude::*,
        types::{PyBytes, PyList},
    },
    std::sync::Arc,
};

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdDecompressionObj {
    dctx: Arc<DCtx<'static>>,
    write_size: usize,
    finished: bool,
}

impl ZstdDecompressionObj {
    pub fn new(dctx: Arc<DCtx<'static>>, write_size: usize) -> PyResult<Self> {
        Ok(ZstdDecompressionObj {
            dctx,
            write_size,
            finished: false,
        })
    }
}

#[pymethods]
impl ZstdDecompressionObj {
    fn decompress<'p>(&mut self, py: Python<'p>, data: PyBuffer<u8>) -> PyResult<&'p PyAny> {
        if self.finished {
            return Err(ZstdError::new_err(
                "cannot use a decompressobj multiple times",
            ));
        }

        if data.len_bytes() == 0 {
            return Ok(PyBytes::new(py, &[]));
        }

        let mut in_buffer = zstd_sys::ZSTD_inBuffer {
            src: data.buf_ptr(),
            size: data.len_bytes(),
            pos: 0,
        };

        let mut dest_buffer: Vec<u8> = Vec::with_capacity(self.write_size);
        let mut out_buffer = zstd_sys::ZSTD_outBuffer {
            dst: dest_buffer.as_mut_ptr() as *mut _,
            size: dest_buffer.capacity(),
            pos: 0,
        };

        let chunks = PyList::empty(py);

        loop {
            let zresult = unsafe {
                zstd_sys::ZSTD_decompressStream(
                    self.dctx.dctx(),
                    &mut out_buffer as *mut _,
                    &mut in_buffer as *mut _,
                )
            };
            if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
                return Err(ZstdError::new_err(format!(
                    "zstd decompressor error: {}",
                    zstd_safe::get_error_name(zresult)
                )));
            }

            if zresult == 0 {
                self.finished = true;
                // TODO clear out decompressor?
            }

            if out_buffer.pos > 0 {
                unsafe {
                    dest_buffer.set_len(out_buffer.pos);
                }

                // TODO avoid buffer copy.
                let chunk = PyBytes::new(py, &dest_buffer);
                chunks.append(chunk)?;
            }

            if zresult == 0 || (in_buffer.pos == in_buffer.size && out_buffer.pos == 0) {
                break;
            }

            out_buffer.pos = 0;
            unsafe {
                dest_buffer.set_len(0);
            }
        }

        let empty = PyBytes::new(py, &[]);
        empty.call_method1("join", (chunks,))
    }

    fn flush<'p>(&self, py: Python<'p>, length: Option<usize>) -> PyResult<&'p PyBytes> {
        Ok(PyBytes::new(py, &[]))
    }
}
