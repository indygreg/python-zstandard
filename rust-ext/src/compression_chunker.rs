// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::compressor::CCtx,
    pyo3::{buffer::PyBuffer, exceptions::PyNotImplementedError, prelude::*},
    std::sync::Arc,
};

#[pyclass]
pub struct ZstdCompressionChunker {
    cctx: Arc<CCtx<'static>>,
    chunk_size: usize,
}

impl ZstdCompressionChunker {
    pub fn new(cctx: Arc<CCtx<'static>>, chunk_size: usize) -> PyResult<Self> {
        Ok(Self { cctx, chunk_size })
    }
}

#[pymethods]
impl ZstdCompressionChunker {
    fn compress<'p>(&self, py: Python<'p>, data: PyBuffer<u8>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn flush<'p>(&self, py: Python<'p>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn finish<'p>(&self, py: Python<'p>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }
}
