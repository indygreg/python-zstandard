// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::ZstdError;
use cpython::exc::{MemoryError, TypeError, ValueError};
use cpython::{
    py_class, py_class_prop_getter, PyCapsule, PyDict, PyErr, PyModule, PyObject, PyResult,
    PyTuple, Python, PythonObject, ToPyObject,
};
use libc::c_int;
use std::marker::PhantomData;

/// Safe wrapper for ZSTD_CCtx_params instances.
pub(crate) struct CCtxParams<'a>(*mut zstd_sys::ZSTD_CCtx_params, PhantomData<&'a ()>);

impl<'a> Drop for CCtxParams<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeCCtxParams(self.0);
        }
    }
}

unsafe impl<'a> Send for CCtxParams<'a> {}
unsafe impl<'a> Sync for CCtxParams<'a> {}

impl<'a> CCtxParams<'a> {
    pub(crate) unsafe fn get_raw_ptr(&self) -> *mut zstd_sys::ZSTD_CCtx_params {
        self.0
    }
}

impl<'a> CCtxParams<'a> {
    pub fn create(py: Python) -> Result<Self, PyErr> {
        let params = unsafe { zstd_sys::ZSTD_createCCtxParams() };
        if params.is_null() {
            return Err(PyErr::new::<MemoryError, _>(
                py,
                "unable to create ZSTD_CCtx_params",
            ));
        }
        Ok(CCtxParams(params, PhantomData))
    }

    pub fn set_parameter(
        &self,
        py: Python,
        param: zstd_sys::ZSTD_cParameter,
        value: i32,
    ) -> PyResult<()> {
        let zresult = unsafe { zstd_sys::ZSTD_CCtxParams_setParameter(self.0, param, value) };
        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            Err(ZstdError::from_message(
                py,
                format!(
                    "unable to set compression context parameter: {}",
                    zstd_safe::get_error_name(zresult)
                )
                .as_ref(),
            ))
        } else {
            Ok(())
        }
    }

    fn apply_compression_parameter(
        &self,
        py: Python,
        params: &ZstdCompressionParameters,
        param: zstd_sys::ZSTD_cParameter,
    ) -> PyResult<()> {
        let value = params.get_raw_parameter(py, param)?;
        self.set_parameter(py, param, value)
    }

    pub fn apply_compression_parameters(
        &self,
        py: Python,
        params: &ZstdCompressionParameters,
    ) -> PyResult<()> {
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_nbWorkers)?;
        // ZSTD_c_format.
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam2,
        )?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_compressionLevel,
        )?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_windowLog)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_hashLog)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_chainLog)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_searchLog)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_minMatch)?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_targetLength,
        )?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_strategy)?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_contentSizeFlag,
        )?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_checksumFlag,
        )?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_dictIDFlag)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_jobSize)?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_overlapLog)?;
        // ZSTD_c_forceMaxWindow
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam3,
        )?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_overlapLog)?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_enableLongDistanceMatching,
        )?;
        self.apply_compression_parameter(py, params, zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashLog)?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmMinMatch,
        )?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmBucketSizeLog,
        )?;
        self.apply_compression_parameter(
            py,
            params,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashRateLog,
        )?;

        Ok(())
    }
}

/// Resolve the value of a compression context parameter.
pub(crate) fn get_cctx_parameter(
    py: Python,
    params: *mut zstd_sys::ZSTD_CCtx_params,
    param: zstd_sys::ZSTD_cParameter,
) -> Result<libc::c_int, PyErr> {
    let mut value: libc::c_int = 0;

    let zresult =
        unsafe { zstd_sys::ZSTD_CCtxParams_getParameter(params, param, &mut value as *mut _) };

    if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
        Err(ZstdError::from_message(
            py,
            format!(
                "unable to retrieve parameter: {}",
                zstd_safe::get_error_name(zresult)
            )
            .as_ref(),
        ))
    } else {
        Ok(value)
    }
}

// Surely there is a better way...
pub(crate) fn int_to_strategy(py: Python, value: u32) -> Result<zstd_sys::ZSTD_strategy, PyErr> {
    if zstd_sys::ZSTD_strategy::ZSTD_fast as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_fast)
    } else if zstd_sys::ZSTD_strategy::ZSTD_dfast as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_dfast)
    } else if zstd_sys::ZSTD_strategy::ZSTD_greedy as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_greedy)
    } else if zstd_sys::ZSTD_strategy::ZSTD_lazy as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_lazy)
    } else if zstd_sys::ZSTD_strategy::ZSTD_lazy2 as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_lazy2)
    } else if zstd_sys::ZSTD_strategy::ZSTD_btlazy2 as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_btlazy2)
    } else if zstd_sys::ZSTD_strategy::ZSTD_btopt as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_btopt)
    } else if zstd_sys::ZSTD_strategy::ZSTD_btultra as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_btultra)
    } else if zstd_sys::ZSTD_strategy::ZSTD_btultra2 as u32 == value {
        Ok(zstd_sys::ZSTD_strategy::ZSTD_btultra2)
    } else {
        Err(PyErr::new::<ValueError, _>(
            py,
            "unknown compression strategy",
        ))
    }
}

pub(crate) unsafe extern "C" fn destroy_cctx_params(o: *mut python3_sys::PyObject) {
    let ptr =
        python3_sys::PyCapsule_GetPointer(o, std::ptr::null()) as *mut zstd_sys::ZSTD_CCtx_params;

    zstd_sys::ZSTD_freeCCtxParams(ptr);
}

py_class!(pub class ZstdCompressionParameters |py| {
    data params: PyCapsule;

    @classmethod def from_level(cls, *args, **kwargs) -> PyResult<PyObject> {
        ZstdCompressionParameters::from_level_impl(py, args, kwargs)
    }

    def __new__(_cls, *args, **kwargs) -> PyResult<ZstdCompressionParameters> {
        ZstdCompressionParameters::new_impl(py, kwargs)
    }

    @property def format(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam2)
    }

    @property def compression_level(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_compressionLevel)
    }

    @property def window_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_windowLog)
    }

    @property def hash_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_hashLog)
    }

    @property def chain_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_chainLog)
    }

    @property def search_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_searchLog)
    }

    @property def min_match(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_minMatch)
    }

    @property def target_length(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_targetLength)
    }

    @property def strategy(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_strategy)
    }

    @property def write_content_size(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_contentSizeFlag)
    }

    @property def write_checksum(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_checksumFlag)
    }

    @property def write_dict_id(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_dictIDFlag)
    }

    @property def job_size(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_jobSize)
    }

    @property def overlap_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_overlapLog)
    }

    @property def force_max_window(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam3)
    }

    @property def enable_ldm(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_enableLongDistanceMatching)
    }

    @property def ldm_hash_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashLog)
    }

    @property def ldm_min_match(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_ldmMinMatch)
    }

    @property def ldm_bucket_size_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_ldmBucketSizeLog)
    }

    @property def ldm_hash_rate_log(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashRateLog)
    }

    @property def threads(&self) -> PyResult<PyObject> {
        self.get_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_nbWorkers)
    }

    def estimated_compression_context_size(&self) -> PyResult<PyObject> {
        self.estimated_compression_context_size_impl(py)
    }
});

impl ZstdCompressionParameters {
    pub(crate) fn get_raw_parameters(&self, py: Python) -> *mut zstd_sys::ZSTD_CCtx_params {
        let capsule: &PyCapsule = self.params(py);

        let params = unsafe {
            python3_sys::PyCapsule_GetPointer(capsule.as_object().as_ptr(), std::ptr::null())
                as *mut zstd_sys::ZSTD_CCtx_params
        };

        params
    }

    fn from_level_impl(py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<PyObject> {
        if args.len(py) != 1 {
            return Err(PyErr::new::<TypeError, _>(
                py,
                format!(
                    "from_level() takes exactly 1 argument ({} given)",
                    args.len(py)
                ),
            ));
        }

        let kwargs: PyDict = if let Some(v) = kwargs {
            v.copy(py)?
        } else {
            PyDict::new(py)
        };

        let level = args.get_item(py, 0).extract::<i32>(py)?;

        let source_size = if let Some(value) = kwargs.get_item(py, "source_size") {
            kwargs.del_item(py, "source_size")?;
            value.extract::<u64>(py)?
        } else {
            0
        };

        let dict_size = if let Some(value) = kwargs.get_item(py, "dict_size") {
            kwargs.del_item(py, "dict_size")?;
            value.extract::<usize>(py)?
        } else {
            0
        };

        let compression_params =
            unsafe { zstd_sys::ZSTD_getCParams(level, source_size, dict_size) };

        if !kwargs.contains(py, "window_log")? {
            kwargs.set_item(py, "window_log", compression_params.windowLog)?;
        }
        if !kwargs.contains(py, "chain_log")? {
            kwargs.set_item(py, "chain_log", compression_params.chainLog)?;
        }
        if !kwargs.contains(py, "hash_log")? {
            kwargs.set_item(py, "hash_log", compression_params.hashLog)?;
        }
        if !kwargs.contains(py, "search_log")? {
            kwargs.set_item(py, "search_log", compression_params.searchLog)?;
        }
        if !kwargs.contains(py, "min_match")? {
            kwargs.set_item(py, "min_match", compression_params.minMatch)?;
        }
        if !kwargs.contains(py, "target_length")? {
            kwargs.set_item(py, "target_length", compression_params.targetLength)?;
        }
        if !kwargs.contains(py, "strategy")? {
            kwargs.set_item(
                py,
                "strategy",
                compression_params.strategy as u32,
            )?;
        }

        let params = unsafe { zstd_sys::ZSTD_createCCtxParams() };

        let ptr = unsafe {
            python3_sys::PyCapsule_New(
                params as *mut _,
                std::ptr::null(),
                Some(destroy_cctx_params),
            )
        };

        if ptr.is_null() {
            unsafe { python3_sys::PyErr_NoMemory() };
            return Err(PyErr::fetch(py));
        }

        let capsule = unsafe { PyObject::from_owned_ptr(py, ptr).unchecked_cast_into() };

        let instance = ZstdCompressionParameters::create_instance(py, capsule)?;

        instance.set_parameters(py, &kwargs)?;

        Ok(instance.into_object())
    }

    fn new_impl(py: Python, kwargs: Option<&PyDict>) -> PyResult<ZstdCompressionParameters> {
        let params = unsafe { zstd_sys::ZSTD_createCCtxParams() };

        let ptr = unsafe {
            python3_sys::PyCapsule_New(
                params as *mut _,
                std::ptr::null(),
                Some(destroy_cctx_params),
            )
        };

        if ptr.is_null() {
            unsafe { python3_sys::PyErr_NoMemory() };
            return Err(PyErr::fetch(py));
        }

        let capsule = unsafe { PyObject::from_owned_ptr(py, ptr).unchecked_cast_into() };

        let instance = ZstdCompressionParameters::create_instance(py, capsule)?;

        let kwargs: PyDict = if let Some(v) = kwargs {
            v.copy(py)?
        } else {
            PyDict::new(py)
        };

        instance.set_parameters(py, &kwargs)?;

        Ok(instance)
    }

    /// Set parameters from a dictionary of options.
    fn set_parameters(&self, py: Python, kwargs: &PyDict) -> PyResult<()> {
        let params = self.get_raw_parameters(py);

        unsafe {
            zstd_sys::ZSTD_CCtxParams_reset(params);
        }

        let mut format = 0;
        let mut compression_level = 0;
        let mut window_log = 0;
        let mut hash_log = 0;
        let mut chain_log = 0;
        let mut search_log = 0;
        let mut min_match = 0;
        let mut target_length = 0;
        let mut strategy = -1;
        let mut write_content_size = 1;
        let mut write_checksum = 0;
        let mut write_dict_id = 0;
        let mut job_size = 0;
        let mut overlap_log = -1;
        let mut force_max_window = 0;
        let mut enable_ldm = 0;
        let mut ldm_hash_log = 0;
        let mut ldm_min_match = 0;
        let mut ldm_bucket_size_log = 0;
        let mut ldm_hash_rate_log = -1;
        let mut threads = 0;

        for (key, value) in kwargs.items(py) {
            let key = key.extract::<String>(py)?;

            match key.as_ref() {
                "format" => format = value.extract::<_>(py)?,
                "compression_level" => compression_level = value.extract::<_>(py)?,
                "window_log" => window_log = value.extract::<_>(py)?,
                "hash_log" => hash_log = value.extract::<_>(py)?,
                "chain_log" => chain_log = value.extract::<_>(py)?,
                "search_log" => search_log = value.extract::<_>(py)?,
                "min_match" => min_match = value.extract::<_>(py)?,
                "target_length" => target_length = value.extract::<_>(py)?,
                "strategy" => strategy = value.extract::<_>(py)?,
                "write_content_size" => write_content_size = value.extract::<_>(py)?,
                "write_checksum" => write_checksum = value.extract::<_>(py)?,
                "write_dict_id" => write_dict_id = value.extract::<_>(py)?,
                "job_size" => job_size = value.extract::<_>(py)?,
                "overlap_log" => overlap_log = value.extract::<_>(py)?,
                "force_max_window" => force_max_window = value.extract::<_>(py)?,
                "enable_ldm" => enable_ldm = value.extract::<_>(py)?,
                "ldm_hash_log" => ldm_hash_log = value.extract::<_>(py)?,
                "ldm_min_match" => ldm_min_match = value.extract::<_>(py)?,
                "ldm_bucket_size_log" => ldm_bucket_size_log = value.extract::<_>(py)?,
                "ldm_hash_rate_log" => ldm_hash_rate_log = value.extract::<_>(py)?,
                "threads" => threads = value.extract::<_>(py)?,
                key => {
                    return Err(PyErr::new::<TypeError, _>(
                        py,
                        format!("'{}' is an invalid keyword argument", key),
                    ))
                }
            }
        }

        if threads < 0 {
            threads = num_cpus::get() as _;
        }

        // We need to set ZSTD_c_nbWorkers before ZSTD_c_jobSize and ZSTD_c_overlapLog
        // because setting ZSTD_c_nbWorkers resets the other parameters.
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_nbWorkers, threads)?;

        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam2,
            format,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_compressionLevel,
            compression_level,
        )?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_windowLog, window_log)?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_hashLog, hash_log)?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_chainLog, chain_log)?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_searchLog, search_log)?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_minMatch, min_match)?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_targetLength,
            target_length,
        )?;

        if strategy == -1 {
            strategy = 0;
        }

        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_strategy, strategy)?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_contentSizeFlag,
            write_content_size,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_checksumFlag,
            write_checksum,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_dictIDFlag,
            write_dict_id,
        )?;
        self.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_jobSize, job_size)?;

        if overlap_log == -1 {
            overlap_log = 0;
        }

        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_overlapLog,
            overlap_log,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_experimentalParam3,
            force_max_window,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_enableLongDistanceMatching,
            enable_ldm,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashLog,
            ldm_hash_log,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmMinMatch,
            ldm_min_match,
        )?;
        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmBucketSizeLog,
            ldm_bucket_size_log,
        )?;

        if ldm_hash_rate_log == -1 {
            ldm_hash_rate_log = 0;
        }

        self.set_parameter(
            py,
            zstd_sys::ZSTD_cParameter::ZSTD_c_ldmHashRateLog,
            ldm_hash_rate_log,
        )?;

        Ok(())
    }

    pub(crate) fn get_raw_parameter(
        &self,
        py: Python,
        param: zstd_sys::ZSTD_cParameter,
    ) -> PyResult<c_int> {
        let params = self.get_raw_parameters(py);

        let mut value: c_int = 0;

        let zresult =
            unsafe { zstd_sys::ZSTD_CCtxParams_getParameter(params, param, &mut value as *mut _) };

        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            return Err(ZstdError::from_message(
                py,
                format!(
                    "unable to retrieve parameter: {}",
                    zstd_safe::get_error_name(zresult)
                )
                .as_ref(),
            ));
        }

        Ok(value)
    }

    fn get_parameter(&self, py: Python, param: zstd_sys::ZSTD_cParameter) -> PyResult<PyObject> {
        let value = self.get_raw_parameter(py, param)?;

        Ok(value.into_py_object(py).into_object())
    }

    fn set_parameter(
        &self,
        py: Python,
        param: zstd_sys::ZSTD_cParameter,
        value: i32,
    ) -> PyResult<()> {
        let capsule: &PyCapsule = self.params(py);

        let params = unsafe {
            python3_sys::PyCapsule_GetPointer(capsule.as_object().as_ptr(), std::ptr::null())
                as *mut zstd_sys::ZSTD_CCtx_params
        };

        let zresult = unsafe { zstd_sys::ZSTD_CCtxParams_setParameter(params, param, value) };

        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            return Err(ZstdError::from_message(
                py,
                format!(
                    "unable to set compression context parameter: {}",
                    zstd_safe::get_error_name(zresult)
                )
                .as_ref(),
            ));
        }

        Ok(())
    }

    fn estimated_compression_context_size_impl(&self, py: Python) -> PyResult<PyObject> {
        let capsule: &PyCapsule = self.params(py);

        let params = unsafe {
            python3_sys::PyCapsule_GetPointer(capsule.as_object().as_ptr(), std::ptr::null())
                as *mut zstd_sys::ZSTD_CCtx_params
        };

        let size = unsafe { zstd_sys::ZSTD_estimateCCtxSize_usingCCtxParams(params) };

        Ok(size.into_py_object(py).into_object())
    }
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(
        py,
        "ZstdCompressionParameters",
        py.get_type::<ZstdCompressionParameters>(),
    )?;

    Ok(())
}
