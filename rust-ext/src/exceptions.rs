// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use cpython::{py_exception, PyErr, PyModule, PyResult, Python};

py_exception!(module, ZstdError);

impl ZstdError {
    pub(crate) fn from_message(py: Python, message: &str) -> PyErr {
        PyErr::new::<ZstdError, _>(py, message)
    }
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "ZstdError", py.get_type::<ZstdError>())?;

    Ok(())
}
