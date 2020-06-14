// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::ZstdError;
use cpython::{py_class, PyModule, PyObject, PyResult, Python, PythonObject};

py_class!(class ZstdCompressor |py| {
    def __new__(
        _cls,
        level: i32 = 3,
        dict_data: Option<PyObject> = None,
        compression_params: Option<PyObject> = None,
        write_checksum: Option<bool> = None,
        write_content_size: Option<bool> = None,
        write_dict_id: Option<bool> = None,
        threads: Option<i32> = None
    ) -> PyResult<PyObject> {
        ZstdCompressor::new_impl(
            py,
            level,
            dict_data,
            compression_params,
            write_checksum,
            write_content_size,
            write_dict_id,
            threads,
        )
    }
});

impl ZstdCompressor {
    fn new_impl(
        py: Python,
        level: i32,
        _dict_data: Option<PyObject>,
        _compression_params: Option<PyObject>,
        _write_checksum: Option<bool>,
        _write_content_size: Option<bool>,
        _write_dict_id: Option<bool>,
        _threads: Option<i32>,
    ) -> PyResult<PyObject> {
        if level > zstd_safe::max_c_level() {
            return Err(ZstdError::from_message(
                py,
                format!(
                    "level must be less than {}",
                    zstd_safe::max_c_level() as i32
                )
                .as_ref(),
            ));
        }

        let compressor = ZstdCompressor::create_instance(py)?;

        Ok(compressor.into_object())
    }
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "ZstdCompressor", py.get_type::<ZstdCompressor>())?;

    Ok(())
}
