// Copyright (c) 2021-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{compression_dict::ZstdCompressionDict, exceptions::ZstdError},
    pyo3::{
        exceptions::{PyMemoryError, PyValueError},
        prelude::*,
    },
    std::{marker::PhantomData, sync::Arc},
};

pub struct DCtx<'a>(*mut zstd_sys::ZSTD_DCtx, PhantomData<&'a ()>);

impl<'a> Drop for DCtx<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeDCtx(self.0);
        }
    }
}

unsafe impl<'a> Send for DCtx<'a> {}
unsafe impl<'a> Sync for DCtx<'a> {}

impl<'a> DCtx<'a> {
    fn new() -> Result<Self, &'static str> {
        let dctx = unsafe { zstd_sys::ZSTD_createDCtx() };
        if dctx.is_null() {
            return Err("could not allocate ZSTD_DCtx instance");
        }

        Ok(Self(dctx, PhantomData))
    }
}

#[pyclass]
struct ZstdDecompressor {
    dict_data: Option<Py<ZstdCompressionDict>>,
    max_window_size: usize,
    format: zstd_sys::ZSTD_format_e,
    dctx: Arc<DCtx<'static>>,
}

impl ZstdDecompressor {
    fn setup_dctx(&self, py: Python, load_dict: bool) -> PyResult<()> {
        unsafe {
            zstd_sys::ZSTD_DCtx_reset(
                self.dctx.0,
                zstd_sys::ZSTD_ResetDirective::ZSTD_reset_session_only,
            );
        }

        if self.max_window_size != 0 {
            let zresult =
                unsafe { zstd_sys::ZSTD_DCtx_setMaxWindowSize(self.dctx.0, self.max_window_size) };
            if unsafe { zstd_sys::ZDICT_isError(zresult) } != 0 {
                return Err(ZstdError::new_err(format!(
                    "unable to set max window size: {}",
                    zstd_safe::get_error_name(zresult)
                )));
            }
        }

        let zresult = unsafe { zstd_sys::ZSTD_DCtx_setFormat(self.dctx.0, self.format) };
        if unsafe { zstd_sys::ZDICT_isError(zresult) } != 0 {
            return Err(ZstdError::new_err(format!(
                "unable to set decoding format: {}",
                zstd_safe::get_error_name(zresult)
            )));
        }

        if let Some(dict_data) = &self.dict_data {
            if load_dict {
                dict_data.try_borrow_mut(py)?.load_into_dctx(self.dctx.0)?;
            }
        }

        Ok(())
    }
}

#[pymethods]
impl ZstdDecompressor {
    #[new]
    #[args(dict_data = "None", max_window_size = "0", format = "0")]
    fn new(
        dict_data: Option<Py<ZstdCompressionDict>>,
        max_window_size: usize,
        format: u32,
    ) -> PyResult<Self> {
        let format = if format == zstd_sys::ZSTD_format_e::ZSTD_f_zstd1 as _ {
            zstd_sys::ZSTD_format_e::ZSTD_f_zstd1
        } else if format == zstd_sys::ZSTD_format_e::ZSTD_f_zstd1_magicless as _ {
            zstd_sys::ZSTD_format_e::ZSTD_f_zstd1_magicless
        } else {
            return Err(PyValueError::new_err(format!("invalid format value")));
        };

        let dctx = Arc::new(DCtx::new().map_err(|_| PyMemoryError::new_err(()))?);

        Ok(Self {
            dict_data,
            max_window_size,
            format,
            dctx,
        })
    }
}

pub(crate) fn init_module(module: &PyModule) -> PyResult<()> {
    module.add_class::<ZstdDecompressor>()?;

    Ok(())
}
