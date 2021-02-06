// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::compressor::CCtx,
    pyo3::{exceptions::PyNotImplementedError, prelude::*},
    std::sync::Arc,
};

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

#[pymethods]
impl ZstdCompressionWriter {
    // TODO __enter__
    // TODO __exit__

    fn memory_size(&self) -> usize {
        self.cctx.memory_size()
    }

    fn fileno(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn close(&self) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[getter]
    fn closed(&self) -> bool {
        self.closed
    }

    fn isatty(&self) -> bool {
        false
    }

    fn readable(&self) -> bool {
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

    #[args(pos, whence = "None")]
    fn seek(&self, pos: isize, whence: Option<&PyAny>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn seekable(&self) -> bool {
        false
    }

    fn truncate(&self, py: Python, size: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn writable(&self) -> bool {
        true
    }

    fn writelines(&self, lines: &PyAny) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(size = "None")]
    fn read(&self, py: Python, size: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn readall(&self, py: Python) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn readinto(&self, py: Python, b: &PyAny) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn write(&self, data: &PyAny) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(flush_mode = "None")]
    fn flush_mode(&self, flush_mode: Option<&PyAny>) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    fn tell(&self) -> usize {
        self.bytes_compressed
    }
}
