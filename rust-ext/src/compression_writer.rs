// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{exceptions::ZstdError, zstd_safe::CCtx},
    pyo3::{
        buffer::PyBuffer,
        exceptions::{PyNotImplementedError, PyOSError, PyValueError},
        prelude::*,
        types::PyBytes,
        PyIterProtocol,
    },
    std::sync::Arc,
};

const FLUSH_BLOCK: usize = 0;
const FLUSH_FRAME: usize = 1;

#[pyclass(module = "zstandard.backend_rust")]
pub struct ZstdCompressionWriter {
    cctx: Arc<CCtx<'static>>,
    writer: PyObject,
    write_return_read: bool,
    closefd: bool,
    entered: bool,
    closing: bool,
    closed: bool,
    bytes_compressed: usize,
    dest_buffer: Vec<u8>,
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
    ) -> PyResult<Self> {
        cctx.set_pledged_source_size(source_size)
            .map_err(|msg| ZstdError::new_err(format!("error setting source size: {}", msg)))?;

        Ok(Self {
            cctx,
            writer: writer.into_py(py),
            write_return_read,
            closefd,
            entered: false,
            closing: false,
            closed: false,
            bytes_compressed: 0,
            dest_buffer: Vec::with_capacity(write_size),
        })
    }
}

#[pymethods]
impl ZstdCompressionWriter {
    fn __enter__<'p>(mut slf: PyRefMut<'p, Self>, _py: Python<'p>) -> PyResult<PyRefMut<'p, Self>> {
        if slf.closed {
            Err(PyValueError::new_err("stream is closed"))
        } else if slf.entered {
            Err(ZstdError::new_err("cannot __enter__ multiple times"))
        } else {
            slf.entered = true;
            Ok(slf)
        }
    }

    fn __exit__<'p>(
        mut slf: PyRefMut<'p, Self>,
        py: Python<'p>,
        _exc_type: &PyAny,
        _exc_value: &PyAny,
        _exc_tb: &PyAny,
    ) -> PyResult<bool> {
        slf.entered = false;
        slf.close(py)?;

        // TODO clear out compressor context?

        Ok(false)
    }

    fn memory_size(&self) -> usize {
        self.cctx.memory_size()
    }

    fn fileno(&self, py: Python) -> PyResult<PyObject> {
        if let Ok(fileno) = self.writer.getattr(py, "fileno") {
            fileno.call0(py)
        } else {
            Err(PyOSError::new_err(
                "filenot not available on underlying writer",
            ))
        }
    }

    fn close(&mut self, py: Python) -> PyResult<()> {
        if self.closed {
            return Ok(());
        }

        self.closing = true;
        let res = self.flush(py, FLUSH_FRAME);
        self.closing = false;
        self.closed = true;

        res?;

        // Call close() on underlying stream as well.
        if let Ok(close) = self.writer.getattr(py, "close") {
            if self.closefd {
                close.call0(py)?;
            }
        }

        Ok(())
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
    #[allow(unused_variables)]
    fn readline(&self, py: Python, size: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    #[args(size = "None")]
    #[allow(unused_variables)]
    fn readlines(&self, py: Python, hint: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    #[args(pos, whence = "None")]
    #[allow(unused_variables)]
    fn seek(&self, py: Python, pos: isize, whence: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn seekable(&self) -> bool {
        false
    }

    #[allow(unused_variables)]
    fn truncate(&self, py: Python, size: Option<&PyAny>) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn writable(&self) -> bool {
        true
    }

    #[allow(unused_variables)]
    fn writelines(&self, lines: &PyAny) -> PyResult<()> {
        Err(PyNotImplementedError::new_err(()))
    }

    #[args(size = "None")]
    #[allow(unused_variables)]
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

    #[allow(unused_variables)]
    fn readinto(&self, py: Python, b: &PyAny) -> PyResult<()> {
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn write(&mut self, py: Python, buffer: PyBuffer<u8>) -> PyResult<usize> {
        if self.closed {
            return Err(PyValueError::new_err("stream is closed"));
        }

        let mut total_write = 0;

        let mut in_buffer = zstd_sys::ZSTD_inBuffer {
            src: buffer.buf_ptr(),
            size: buffer.len_bytes(),
            pos: 0,
        };

        while in_buffer.pos < in_buffer.size {
            self.cctx
                .compress_into_vec(
                    &mut self.dest_buffer,
                    &mut in_buffer,
                    zstd_sys::ZSTD_EndDirective::ZSTD_e_continue,
                )
                .map_err(|msg| ZstdError::new_err(format!("zstd compress error: {}", msg)))?;

            if !self.dest_buffer.is_empty() {
                // TODO avoid buffer copy.
                let chunk = PyBytes::new(py, &self.dest_buffer);
                self.writer.call_method1(py, "write", (chunk,))?;

                total_write += self.dest_buffer.len();
                self.bytes_compressed += self.dest_buffer.len();
                self.dest_buffer.clear();
            }
        }

        if self.write_return_read {
            Ok(in_buffer.pos)
        } else {
            Ok(total_write)
        }
    }

    #[args(flush_mode = "FLUSH_BLOCK")]
    fn flush(&mut self, py: Python, flush_mode: usize) -> PyResult<usize> {
        let flush = match flush_mode {
            FLUSH_BLOCK => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_flush),
            FLUSH_FRAME => Ok(zstd_sys::ZSTD_EndDirective::ZSTD_e_end),
            _ => Err(PyValueError::new_err(format!(
                "unknown flush_mode: {}",
                flush_mode
            ))),
        }?;

        if self.closed {
            return Err(PyValueError::new_err("stream is closed"));
        }

        let mut total_write = 0;

        let mut in_buffer = zstd_sys::ZSTD_inBuffer {
            src: std::ptr::null_mut(),
            size: 0,
            pos: 0,
        };

        loop {
            let zresult = self
                .cctx
                .compress_into_vec(&mut self.dest_buffer, &mut in_buffer, flush)
                .map_err(|msg| ZstdError::new_err(format!("zstd compress error: {}", msg)))?;

            if !self.dest_buffer.is_empty() {
                // TODO avoid buffer copy.
                let chunk = PyBytes::new(py, &self.dest_buffer);
                self.writer.call_method1(py, "write", (chunk,))?;

                total_write += self.dest_buffer.len();
                self.bytes_compressed += self.dest_buffer.len();
                self.dest_buffer.clear();
            }

            if zresult == 0 {
                break;
            }
        }

        if let Ok(flush) = self.writer.getattr(py, "flush") {
            if !self.closing {
                flush.call0(py)?;
            }
        }

        Ok(total_write)
    }

    fn tell(&self) -> usize {
        self.bytes_compressed
    }
}

#[pyproto]
impl PyIterProtocol for ZstdCompressionWriter {
    fn __iter__(slf: PyRef<Self>) -> PyResult<()> {
        let py = slf.py();
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }

    fn __next__(slf: PyRef<Self>) -> PyResult<Option<()>> {
        let py = slf.py();
        let io = py.import("io")?;
        let exc = io.getattr("UnsupportedOperation")?;

        Err(PyErr::from_instance(exc))
    }
}
