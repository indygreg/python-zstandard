// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::exceptions::ZstdError,
    pyo3::{
        buffer::PyBuffer,
        class::{PyBufferProtocol, PySequenceProtocol},
        exceptions::{PyIndexError, PyTypeError, PyValueError},
        ffi::Py_buffer,
        prelude::*,
        types::{PyBytes, PyTuple},
        AsPyPointer,
    },
};

#[repr(C)]
#[derive(Clone, Debug)]
pub(crate) struct BufferSegment {
    pub offset: u64,
    pub length: u64,
}

#[pyclass(module = "zstandard.backend_rust", name = "BufferSegment")]
pub struct ZstdBufferSegment {
    /// The object backing storage. For reference counting.
    _parent: PyObject,
    /// PyBuffer into parent object.
    buffer: PyBuffer<u8>,
    /// Offset of segment within data.
    offset: usize,
    /// Length of segment within data.
    len: usize,
}

impl ZstdBufferSegment {
    pub fn as_slice(&self) -> &[u8] {
        unsafe {
            std::slice::from_raw_parts(self.buffer.buf_ptr().add(self.offset) as *const _, self.len)
        }
    }
}

#[pymethods]
impl ZstdBufferSegment {
    #[getter]
    fn offset(&self) -> usize {
        self.offset
    }

    fn tobytes<'p>(&self, py: Python<'p>) -> PyResult<&'p PyBytes> {
        Ok(PyBytes::new(py, self.as_slice()))
    }
}

#[pyproto]
impl PySequenceProtocol for ZstdBufferSegment {
    fn __len__(&self) -> usize {
        self.len
    }
}

#[pyproto]
impl PyBufferProtocol for ZstdBufferSegment {
    fn bf_getbuffer(slf: PyRefMut<Self>, view: *mut Py_buffer, flags: i32) -> PyResult<()> {
        let slice = slf.as_slice();

        if unsafe {
            pyo3::ffi::PyBuffer_FillInfo(
                view,
                slf.as_ptr(),
                slice.as_ptr() as *mut _,
                slice.len() as _,
                1,
                flags,
            )
        } != 0
        {
            Err(PyErr::fetch(slf.py()))
        } else {
            Ok(())
        }
    }

    #[allow(unused_variables)]
    fn bf_releasebuffer(slf: PyRefMut<Self>, view: *mut Py_buffer) {}
}

#[pyclass(module = "zstandard.backend_rust", name = "BufferSegments")]
pub struct ZstdBufferSegments {
    parent: PyObject,
}

#[pyproto]
impl PyBufferProtocol for ZstdBufferSegments {
    fn bf_getbuffer(slf: PyRefMut<Self>, view: *mut Py_buffer, flags: i32) -> PyResult<()> {
        let py = slf.py();

        let parent: &PyCell<ZstdBufferWithSegments> = slf.parent.extract(py)?;

        if unsafe {
            pyo3::ffi::PyBuffer_FillInfo(
                view,
                slf.as_ptr(),
                parent.borrow().segments.as_ptr() as *const _ as *mut _,
                (parent.borrow().segments.len() * std::mem::size_of::<BufferSegment>()) as isize,
                1,
                flags,
            )
        } != 0
        {
            Err(PyErr::fetch(py))
        } else {
            Ok(())
        }
    }

    #[allow(unused_variables)]
    fn bf_releasebuffer(slf: PyRefMut<Self>, view: *mut Py_buffer) {}
}

#[pyclass(module = "zstandard.backend_rust", name = "BufferWithSegments")]
pub struct ZstdBufferWithSegments {
    source: PyObject,
    pub(crate) buffer: PyBuffer<u8>,
    pub(crate) segments: Vec<BufferSegment>,
}

impl ZstdBufferWithSegments {
    fn as_slice(&self) -> &[u8] {
        unsafe {
            std::slice::from_raw_parts(self.buffer.buf_ptr() as *const _, self.buffer.len_bytes())
        }
    }

    pub fn get_segment_slice<'p>(&self, _py: Python<'p>, i: usize) -> &'p [u8] {
        let segment = &self.segments[i];

        unsafe {
            std::slice::from_raw_parts(
                self.buffer.buf_ptr().add(segment.offset as usize) as *const _,
                segment.length as usize,
            )
        }
    }
}

#[pymethods]
impl ZstdBufferWithSegments {
    #[new]
    pub fn new(py: Python, data: &PyAny, segments: PyBuffer<u8>) -> PyResult<Self> {
        let data_buffer = PyBuffer::get(data)?;

        if segments.len_bytes() % std::mem::size_of::<BufferSegment>() != 0 {
            return Err(PyValueError::new_err(format!(
                "segments array size is not a multiple of {}",
                std::mem::size_of::<BufferSegment>()
            )));
        }

        let segments_slice: &[BufferSegment] = unsafe {
            std::slice::from_raw_parts(
                segments.buf_ptr() as *const _,
                segments.len_bytes() / std::mem::size_of::<BufferSegment>(),
            )
        };

        // Make a copy of the segments data. It is cheap to do so and is a
        // guard against caller changing offsets, which has security implications.
        let segments = segments_slice.to_vec();

        // Validate segments data, as blindly trusting it could lead to
        // arbitrary memory access.
        for segment in &segments {
            if segment.offset + segment.length > data_buffer.len_bytes() as _ {
                return Err(PyValueError::new_err(
                    "offset within segments array references memory outside buffer",
                ));
            }
        }

        Ok(Self {
            source: data.into_py(py),
            buffer: data_buffer,
            segments,
        })
    }

    #[getter]
    fn size(&self) -> usize {
        self.buffer.len_bytes()
    }

    fn segments(slf: PyRef<Self>, py: Python) -> PyResult<ZstdBufferSegments> {
        Ok(ZstdBufferSegments {
            // TODO surely there is a better way to cast self to PyObject?
            parent: unsafe { Py::from_borrowed_ptr(py, slf.as_ptr()) },
        })
    }

    fn tobytes<'p>(&self, py: Python<'p>) -> PyResult<&'p PyBytes> {
        Ok(PyBytes::new(py, self.as_slice()))
    }
}

#[pyproto]
impl PySequenceProtocol for ZstdBufferWithSegments {
    fn __len__(&self) -> usize {
        self.segments.len()
    }

    fn __getitem__(&self, key: isize) -> PyResult<ZstdBufferSegment> {
        let py = unsafe { Python::assume_gil_acquired() };

        if key < 0 {
            return Err(PyIndexError::new_err("offset must be non-negative"));
        }

        let key = key as usize;

        if key >= self.segments.len() {
            return Err(PyIndexError::new_err(format!(
                "offset must be less than {}",
                self.segments.len()
            )));
        }

        let segment = &self.segments[key];

        Ok(ZstdBufferSegment {
            _parent: self.source.clone_ref(py),
            buffer: PyBuffer::get(self.source.extract(py)?)?,
            offset: segment.offset as _,
            len: segment.length as _,
        })
    }
}

#[pyproto]
impl PyBufferProtocol for ZstdBufferWithSegments {
    fn bf_getbuffer(slf: PyRefMut<Self>, view: *mut Py_buffer, flags: i32) -> PyResult<()> {
        if unsafe {
            pyo3::ffi::PyBuffer_FillInfo(
                view,
                slf.as_ptr(),
                slf.buffer.buf_ptr(),
                slf.buffer.len_bytes() as _,
                1,
                flags,
            )
        } != 0
        {
            Err(PyErr::fetch(slf.py()))
        } else {
            Ok(())
        }
    }

    #[allow(unused_variables)]
    fn bf_releasebuffer(slf: PyRefMut<Self>, view: *mut Py_buffer) {}
}

#[pyclass(
    module = "zstandard.backend_rust",
    name = "BufferWithSegmentsCollection"
)]
pub struct ZstdBufferWithSegmentsCollection {
    // Py<ZstdBufferWithSegments>.
    pub(crate) buffers: Vec<PyObject>,
    first_elements: Vec<usize>,
}

#[pymethods]
impl ZstdBufferWithSegmentsCollection {
    #[new]
    #[args(py_args = "*")]
    pub fn new(py: Python, py_args: &PyTuple) -> PyResult<Self> {
        if py_args.is_empty() {
            return Err(PyValueError::new_err("must pass at least 1 argument"));
        }

        let mut buffers = Vec::with_capacity(py_args.len());
        let mut first_elements = Vec::with_capacity(py_args.len());
        let mut offset = 0;

        for item in py_args {
            let item: &PyCell<ZstdBufferWithSegments> = item.extract().map_err(|_| {
                PyTypeError::new_err("arguments must be BufferWithSegments instances")
            })?;
            let segment = item.borrow();

            if segment.segments.is_empty() || segment.buffer.len_bytes() == 0 {
                return Err(PyValueError::new_err(
                    "ZstdBufferWithSegments cannot be empty",
                ));
            }

            offset += segment.segments.len();

            buffers.push(item.to_object(py));
            first_elements.push(offset);
        }

        Ok(Self {
            buffers,
            first_elements,
        })
    }

    fn size(&self, py: Python) -> PyResult<usize> {
        let mut size = 0;

        for buffer in &self.buffers {
            let item: &PyCell<ZstdBufferWithSegments> = buffer.extract(py)?;

            for segment in &item.borrow().segments {
                size += segment.length as usize;
            }
        }

        Ok(size)
    }
}

#[pyproto]
impl PySequenceProtocol for ZstdBufferWithSegmentsCollection {
    fn __len__(&self) -> usize {
        self.first_elements.last().unwrap().clone()
    }

    fn __getitem__(&self, key: isize) -> PyResult<ZstdBufferSegment> {
        let py = unsafe { Python::assume_gil_acquired() };

        if key < 0 {
            return Err(PyIndexError::new_err("offset must be non-negative"));
        }

        let key = key as usize;

        if key >= self.__len__() {
            return Err(PyIndexError::new_err(format!(
                "offset must be less than {}",
                self.__len__()
            )));
        }

        let mut offset = 0;
        for (buffer_index, segment) in self.buffers.iter().enumerate() {
            if key < self.first_elements[buffer_index] {
                if buffer_index > 0 {
                    offset = self.first_elements[buffer_index - 1];
                }

                let item: &PyCell<ZstdBufferWithSegments> = segment.extract(py)?;

                return item.borrow().__getitem__((key - offset) as isize);
            }
        }

        Err(ZstdError::new_err(
            "error resolving segment; this should not happen",
        ))
    }
}

pub(crate) fn init_module(module: &PyModule) -> PyResult<()> {
    module.add_class::<ZstdBufferSegment>()?;
    module.add_class::<ZstdBufferSegments>()?;
    module.add_class::<ZstdBufferWithSegments>()?;
    module.add_class::<ZstdBufferWithSegmentsCollection>()?;

    Ok(())
}
