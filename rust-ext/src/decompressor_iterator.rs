// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{
        decompressor::DCtx,
        exceptions::ZstdError,
        stream::{make_in_buffer_source, InBufferSource},
    },
    pyo3::{exceptions::PyValueError, prelude::*, types::PyBytes, PyIterProtocol},
    std::{cmp::min, sync::Arc},
};

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdDecompressorIterator {
    dctx: Arc<DCtx<'static>>,
    source: Box<dyn InBufferSource + Send>,
    write_size: usize,
    finished_output: bool,
}

impl ZstdDecompressorIterator {
    pub fn new(
        py: Python,
        dctx: Arc<DCtx<'static>>,
        reader: &PyAny,
        read_size: usize,
        write_size: usize,
        skip_bytes: usize,
    ) -> PyResult<Self> {
        let mut source = make_in_buffer_source(py, reader, read_size)?;

        let mut skip_bytes = skip_bytes;
        while skip_bytes > 0 {
            let in_buffer = source
                .input_buffer(py)?
                .ok_or_else(|| PyValueError::new_err("skip_bytes larger than first input chunk"))?;

            let read = min(skip_bytes, in_buffer.size - in_buffer.pos);
            source.record_bytes_read(read);
            skip_bytes -= read;
        }

        Ok(Self {
            dctx,
            source,
            write_size,
            finished_output: false,
        })
    }
}

#[pyproto]
impl PyIterProtocol for ZstdDecompressorIterator {
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

        // While input is available.
        while let Some(mut in_buffer) = slf.source.input_buffer(py)? {
            let zresult = unsafe {
                zstd_sys::ZSTD_decompressStream(
                    slf.dctx.dctx(),
                    &mut out_buffer as *mut _,
                    &mut in_buffer as *mut _,
                )
            };
            if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
                return Err(ZstdError::new_err(format!(
                    "zstd decompress error: {}",
                    zstd_safe::get_error_name(zresult)
                )));
            }

            slf.source.record_bytes_read(in_buffer.pos);
            unsafe {
                dest_buffer.set_len(out_buffer.pos);
            }

            // Emit chunk if output buffer is full.
            if out_buffer.pos == out_buffer.size {
                // TODO avoid buffer copy.
                let chunk = PyBytes::new(py, &dest_buffer);
                return Ok(Some(chunk.into_py(py)));
            }

            // Try to get more input to fill output buffer.
            continue;
        }

        // Input is exhausted. Emit what we have or finish.
        if out_buffer.pos > 0 {
            // TODO avoid buffer copy.
            let chunk = PyBytes::new(py, &dest_buffer);
            Ok(Some(chunk.into_py(py)))
        } else {
            Ok(None)
        }
    }
}
