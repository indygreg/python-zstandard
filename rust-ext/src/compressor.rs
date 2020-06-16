// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::compression_dict::ZstdCompressionDict;
use crate::compression_parameters::ZstdCompressionParameters;
use cpython::exc::ValueError;
use cpython::{py_class, PyErr, PyModule, PyObject, PyResult, Python, PythonObject};

py_class!(class ZstdCompressor |py| {
    def __new__(
        _cls,
        level: i32 = 3,
        dict_data: Option<ZstdCompressionDict> = None,
        compression_params: Option<ZstdCompressionParameters> = None,
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
        _dict_data: Option<ZstdCompressionDict>,
        _compression_params: Option<ZstdCompressionParameters>,
        _write_checksum: Option<bool>,
        _write_content_size: Option<bool>,
        _write_dict_id: Option<bool>,
        _threads: Option<i32>,
    ) -> PyResult<PyObject> {
        if level > zstd_safe::max_c_level() {
            return Err(PyErr::new::<ValueError, _>(
                py,
                format!(
                    "level must be less than {}",
                    zstd_safe::max_c_level() as i32 + 1
                ),
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
