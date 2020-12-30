// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {crate::compressor::CCtx, pyo3::prelude::*, std::sync::Arc};

#[pyclass]
pub struct ZstdCompressionWriter {
    cctx: Arc<CCtx<'static>>,
    writer: PyObject,
    source_size: u64,
    write_size: usize,
    write_return_read: bool,
    closefd: bool,
    entered: bool,
    closing: bool,
    closed: bool,
    bytes_compressed: usize,
}

impl ZstdCompressionWriter {
    pub fn new(
        py: Python,
        cctx: Arc<CCtx<'static>>,
        writer: &PyAny,
        source_size: u64,
        write_size: usize,
        write_return_read: bool,
        closefd: bool,
    ) -> Self {
        Self {
            cctx,
            writer: writer.into_py(py),
            source_size,
            write_size,
            write_return_read,
            closefd,
            entered: false,
            closing: false,
            closed: false,
            bytes_compressed: 0,
        }
    }
}
