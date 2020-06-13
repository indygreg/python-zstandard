// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::ZstdError;
use cpython::buffer::PyBuffer;
use cpython::{
    py_class, py_class_prop_getter, py_fn, PyModule, PyObject, PyResult, Python, PythonObject,
    ToPyObject,
};

py_class!(class FrameParameters |py| {
    data header: zstd_sys::ZSTD_frameHeader;

    @property def content_size(&self) -> PyResult<PyObject> {
        Ok(self.header(py).frameContentSize.into_py_object(py).into_object())
    }

    @property def window_size(&self) -> PyResult<PyObject> {
        Ok(self.header(py).windowSize.into_py_object(py).into_object())
    }

    @property def dict_id(&self) -> PyResult<PyObject> {
        Ok(self.header(py).dictID.into_py_object(py).into_object())
    }

    @property def has_checksum(&self) -> PyResult<PyObject> {
        Ok(match self.header(py).checksumFlag {
            0 => false,
            _ => true,
        }.into_py_object(py).into_object())
    }
});

fn get_frame_parameters(py: Python, data: PyObject) -> PyResult<PyObject> {
    let buffer = PyBuffer::get(py, &data)?;

    let raw_data = unsafe {
        std::slice::from_raw_parts::<u8>(buffer.buf_ptr() as *const _, buffer.len_bytes())
    };

    let mut header = zstd_sys::ZSTD_frameHeader {
        frameContentSize: 0,
        windowSize: 0,
        blockSizeMax: 0,
        frameType: zstd_sys::ZSTD_frameType_e::ZSTD_frame,
        headerSize: 0,
        dictID: 0,
        checksumFlag: 0,
    };
    let zresult = unsafe {
        zstd_sys::ZSTD_getFrameHeader(&mut header, raw_data.as_ptr() as *const _, raw_data.len())
    };

    if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
        Err(ZstdError::from_message(
            py,
            format!(
                "cannot get frame parameters: {}",
                zstd_safe::get_error_name(zresult)
            )
            .as_ref(),
        ))
    } else if zresult != 0 {
        Err(ZstdError::from_message(
            py,
            format!(
                "not enough data for frame parameters; need {} bytes",
                zresult
            )
            .as_ref(),
        ))
    } else {
        Ok(FrameParameters::create_instance(py, header)?.into_object())
    }
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "FrameParameters", py.get_type::<FrameParameters>())?;
    module.add(
        py,
        "get_frame_parameters",
        py_fn!(py, get_frame_parameters(data: PyObject)),
    )?;

    Ok(())
}
