// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::compressor::CCtx,
    pyo3::{
        exceptions::{PyNotImplementedError, PyOSError},
        prelude::*,
    },
    std::sync::Arc,
};

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdCompressionReader {
    cctx: Arc<CCtx<'static>>,
    reader: PyObject,
    read_size: usize,
    closefd: bool,
}

impl ZstdCompressionReader {
    pub fn new(
        py: Python,
        cctx: Arc<CCtx<'static>>,
        reader: &PyAny,
        read_size: usize,
        closefd: bool,
    ) -> PyResult<Self> {
        Ok(Self {
            cctx,
            reader: reader.into_py(py),
            read_size,
            closefd,
        })
    }
}

#[pymethods]
impl ZstdCompressionReader {
    // TODO __enter__
    // TODO __exit__

    fn readable(&self) -> bool {
        true
    }

    fn writable(&self) -> bool {
        false
    }

    fn seekable(&self) -> bool {
        false
    }

    fn readline(&self, py: Python) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn readlines(&self, py: Python) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn write(&self, _data: &PyAny) -> PyResult<()> {
        Err(PyOSError::new_err("stream is not writable"))
    }

    fn writelines(&self, _data: &PyAny) -> PyResult<()> {
        Err(PyOSError::new_err("stream is not writable"))
    }

    fn isatty(&self) -> bool {
        false
    }

    fn flush(&self) -> PyResult<()> {
        Ok(())
    }

    fn close(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[getter]
    fn closed(&self) -> PyResult<bool> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn tell(&self) -> PyResult<usize> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn readall(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    // TODO __iter__
    // TODO __next__

    #[args(size = "None")]
    fn read(&self, size: Option<usize>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(size = "None")]
    fn read1(&self, size: Option<usize>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn readinto(&self, b: &PyAny) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn readinto1(&self, b: &PyAny) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }
}
