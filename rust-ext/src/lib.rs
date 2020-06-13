// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use cpython::{py_module_initializer, Python, PyModule, PyResult};

// add bindings to the generated python module
// N.B: names: "rust2py" must be the name of the `.so` or `.pyd` file
py_module_initializer!(zstandard_oxidized, |py, m| {
    init_module(py, m)
});

fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "__doc__", "Rust backend for zstandard bindings")?;

    Ok(())
}