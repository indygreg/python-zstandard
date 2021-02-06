// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::decompressor::DCtx,
    pyo3::{buffer::PyBuffer, exceptions::PyNotImplementedError, prelude::*},
    std::sync::Arc,
};

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdDecompressionReader {
    dctx: Arc<DCtx<'static>>,
    reader: PyObject,
    read_size: usize,
    read_across_frames: bool,
    closefd: bool,
}

impl ZstdDecompressionReader {
    pub fn new(
        py: Python,
        dctx: Arc<DCtx<'static>>,
        reader: &PyAny,
        read_size: usize,
        read_across_frames: bool,
        closefd: bool,
    ) -> PyResult<Self> {
        Ok(Self {
            dctx,
            reader: reader.into_py(py),
            read_size,
            read_across_frames,
            closefd,
        })
    }
}

#[pymethods]
impl ZstdDecompressionReader {
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

    #[args(size = "None")]
    fn readline(&self, py: Python, _size: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    #[args(size = "None")]
    fn readlines(&self, py: Python, _hint: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn write(&self, py: Python, _data: &PyAny) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn writelines(&self, py: Python, _lines: &PyAny) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
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
    fn closed(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn tell(&self) -> PyResult<()> {
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

    fn readinto(&self, buffer: PyBuffer<u8>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(size = "None")]
    fn read1(&self, size: Option<usize>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn readinto1(&self, buffer: PyBuffer<u8>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(pos, whence = "None")]
    fn seek(&self, pos: isize, whence: Option<i32>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }
}
