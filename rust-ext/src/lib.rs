// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use cpython::{py_module_initializer, PyModule, PyResult, Python};

mod constants;

const VERSION: &'static str = "0.15.0.dev0";

py_module_initializer!(zstandard_oxidized, |py, m| { init_module(py, m) });

fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    crate::constants::init_module(py, module)?;

    Ok(())
}
