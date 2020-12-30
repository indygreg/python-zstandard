// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use pyo3::{prelude::*, types::PySet};

mod compression_dict;
mod compression_parameters;
mod compressionobj;
mod compressor;
mod constants;
mod exceptions;
mod frame_parameters;

use exceptions::ZstdError;

const VERSION: &'static str = "0.16.0.dev0";

#[pymodule]
fn backend_rust(py: Python, module: &PyModule) -> PyResult<()> {
    let features = PySet::empty(py)?;
    module.add("backend_features", features)?;

    crate::compression_dict::init_module(module)?;
    crate::compression_parameters::init_module(module)?;
    crate::compressor::init_module(module)?;
    crate::constants::init_module(py, module)?;
    crate::exceptions::init_module(py, module)?;
    crate::frame_parameters::init_module(module)?;

    Ok(())
}
