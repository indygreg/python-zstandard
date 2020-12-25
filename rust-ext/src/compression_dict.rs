// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::compression_parameters::{
    get_cctx_parameter, int_to_strategy, ZstdCompressionParameters,
};
use crate::ZstdError;
use cpython::buffer::PyBuffer;
use cpython::exc::ValueError;
use cpython::{
    py_class, py_class_prop_getter, py_fn, PyBytes, PyErr, PyList, PyModule, PyObject, PyResult,
    Python, PythonObject,
};
use std::cell::RefCell;
use std::marker::PhantomData;

/// Safe wrapper for ZSTD_CDict instances.
pub struct CDict<'a>(*mut zstd_sys::ZSTD_CDict, PhantomData<&'a ()>);

impl<'a> Drop for CDict<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeCDict(self.0);
        }
    }
}

unsafe impl<'a> Send for CDict<'a> {}
unsafe impl<'a> Sync for CDict<'a> {}

/// Holds state for a ZstdCompressionDict.
pub struct DictState {
    /// Internal format of dictionary data.
    content_type: zstd_sys::ZSTD_dictContentType_e,
    /// Raw dictionary data.
    ///
    /// Owned by us.
    data: Vec<u8>,
    /// Segment size.
    k: u32,
    /// Dmer size.
    d: u32,
    /// Precomputed compression dictionary.
    cdict: Option<CDict<'static>>,
}

py_class!(pub class ZstdCompressionDict |py| {
    data state: RefCell<DictState>;

    def __new__(_cls, data: PyObject, dict_type: Option<u32> = None
    ) -> PyResult<PyObject> {
        ZstdCompressionDict::new_impl(py, data, dict_type)
    }

    @property def k(&self) -> PyResult<u32> {
        Ok(self.state(py).borrow().k)
    }

    @property def d(&self) -> PyResult<u32> {
        Ok(self.state(py).borrow().d)
    }

    def __len__(&self) -> PyResult<usize> {
        Ok(self.state(py).borrow().data.len())
    }

    def as_bytes(&self) -> PyResult<PyBytes> {
        Ok(PyBytes::new(py, &self.state(py).borrow().data))
    }

    def dict_id(&self) -> PyResult<u32> {
        Ok(zstd_safe::get_dict_id(&self.state(py).borrow().data).unwrap_or(0))
    }

    def precompute_compress(
        &self,
        level: Option<i32> = None,
        compression_params: Option<ZstdCompressionParameters> = None
    ) -> PyResult<PyObject> {
        self.precompute_compress_impl(py, level, compression_params)
    }
});

impl ZstdCompressionDict {
    fn new_impl(py: Python, data: PyObject, dict_type: Option<u32>) -> PyResult<PyObject> {
        let buffer = PyBuffer::get(py, &data)?;

        let dict_type = if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto as u32)
        {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto)
        } else if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict as u32) {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict)
        } else if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_rawContent as u32) {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_rawContent)
        } else if let Some(value) = dict_type {
            Err(PyErr::new::<ValueError, _>(
                py,
                format!(
                    "invalid dictionary load mode: {}; must use DICT_TYPE_* constants",
                    value
                ),
            ))
        } else {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto)
        }?;

        let dict_data = buffer.to_vec::<u8>(py)?;

        let state = RefCell::new(DictState {
            content_type: dict_type,
            data: dict_data,
            k: 0,
            d: 0,
            cdict: None,
        });

        Ok(ZstdCompressionDict::create_instance(py, state)?.into_object())
    }

    fn precompute_compress_impl(
        &self,
        py: Python,
        level: Option<i32>,
        compression_params: Option<ZstdCompressionParameters>,
    ) -> PyResult<PyObject> {
        let mut state: std::cell::RefMut<DictState> = self.state(py).borrow_mut();

        let params = if let Some(level) = level {
            if compression_params.is_some() {
                return Err(PyErr::new::<ValueError, _>(
                    py,
                    "must only specify one of level or compression_params",
                ));
            }

            unsafe { zstd_sys::ZSTD_getCParams(level, 0, state.data.len()) }
        } else if let Some(compression_params) = compression_params {
            let source_params = compression_params.get_raw_parameters(py);

            let window_log = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_windowLog,
            )?;
            let chain_log = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_chainLog,
            )?;
            let hash_log =
                get_cctx_parameter(py, source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_hashLog)?;
            let search_log = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_searchLog,
            )?;
            let min_match = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_minMatch,
            )?;
            let target_length = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_targetLength,
            )?;
            let strategy = get_cctx_parameter(
                py,
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_strategy,
            )?;

            zstd_sys::ZSTD_compressionParameters {
                windowLog: window_log as u32,
                chainLog: chain_log as u32,
                hashLog: hash_log as u32,
                searchLog: search_log as u32,
                minMatch: min_match as u32,
                targetLength: target_length as u32,
                strategy: int_to_strategy(py, strategy as u32)?,
            }
        } else {
            return Err(PyErr::new::<ValueError, _>(
                py,
                "must specify one of level or compression_params",
            ));
        };

        let cdict = unsafe {
            zstd_sys::ZSTD_createCDict_advanced(
                state.data.as_ptr() as *const _,
                state.data.len(),
                zstd_sys::ZSTD_dictLoadMethod_e::ZSTD_dlm_byRef,
                state.content_type,
                params,
                zstd_sys::ZSTD_customMem {
                    customAlloc: None,
                    customFree: None,
                    opaque: std::ptr::null_mut(),
                },
            )
        };

        if cdict.is_null() {
            return Err(ZstdError::from_message(
                py,
                "unable to precompute dictionary",
            ));
        }

        state.cdict = Some(CDict(cdict, PhantomData));

        Ok(py.None())
    }

    pub(crate) fn load_into_cctx(
        &self,
        py: Python,
        cctx: *mut zstd_sys::ZSTD_CCtx,
    ) -> PyResult<()> {
        let state: std::cell::Ref<DictState> = self.state(py).borrow();

        let zresult = if let Some(cdict) = &state.cdict {
            unsafe { zstd_sys::ZSTD_CCtx_refCDict(cctx, cdict.0) }
        } else {
            unsafe {
                zstd_sys::ZSTD_CCtx_loadDictionary_advanced(
                    cctx,
                    state.data.as_ptr() as *const _,
                    state.data.len(),
                    zstd_sys::ZSTD_dictLoadMethod_e::ZSTD_dlm_byRef,
                    state.content_type,
                )
            }
        };

        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            Err(ZstdError::from_message(
                py,
                format!(
                    "could not load compression dictionary: {}",
                    zstd_safe::get_error_name(zresult)
                )
                .as_ref(),
            ))
        } else {
            Ok(())
        }
    }
}

fn train_dictionary(
    py: Python,
    dict_size: usize,
    samples: PyObject,
    k: u32,
    d: u32,
    f: u32,
    split_point: f64,
    accel: u32,
    notifications: u32,
    dict_id: u32,
    level: i32,
    steps: u32,
    threads: i32,
) -> PyResult<PyObject> {
    let samples = samples.cast_into::<PyList>(py)?;

    let threads = if threads < 0 {
        num_cpus::get() as u32
    } else {
        threads as u32
    };

    let (d, steps, level) = if steps == 0 && threads == 0 {
        // Defaults from ZDICT_trainFromBuffer().
        let d = if d != 0 { d } else { 8 };
        let steps = if steps != 0 { steps } else { 4 };
        let level = if level != 0 { level } else { 3 };

        (d, steps, level)
    } else {
        (d, steps, level)
    };

    let params = zstd_sys::ZDICT_fastCover_params_t {
        k,
        d,
        f,
        steps,
        nbThreads: threads,
        splitPoint: split_point,
        accel,
        shrinkDict: 0,
        shrinkDictMaxRegression: 0,
        zParams: zstd_sys::ZDICT_params_t {
            compressionLevel: level,
            notificationLevel: notifications,
            dictID: dict_id,
        },
    };

    let mut samples_len = 0;

    // Figure out total size of input samples. A side-effect is all elements are
    // validated to be PyBytes.
    for sample in samples.iter(py) {
        let bytes = sample
            .cast_as::<PyBytes>(py)
            .or_else(|_| Err(PyErr::new::<ValueError, _>(py, "samples must be bytes")))?;

        samples_len += bytes.data(py).len();
    }

    let mut samples_buffer: Vec<u8> = Vec::with_capacity(samples_len);
    let mut sample_sizes: Vec<libc::size_t> = Vec::with_capacity(samples.len(py));

    for sample in samples.iter(py) {
        // We validated type above.
        let bytes = unsafe { sample.unchecked_cast_as::<PyBytes>() };
        let data = bytes.data(py);
        sample_sizes.push(data.len());
        samples_buffer.extend_from_slice(data);
    }

    let mut dict_data: Vec<u8> = Vec::with_capacity(dict_size);

    let zresult = py.allow_threads(|| unsafe {
        zstd_sys::ZDICT_optimizeTrainFromBuffer_fastCover(
            dict_data.as_mut_ptr() as *mut _,
            dict_data.capacity(),
            samples_buffer.as_ptr() as *const _,
            sample_sizes.as_ptr(),
            sample_sizes.len() as u32,
            &params as *const _ as *mut _,
        )
    });

    if unsafe { zstd_sys::ZDICT_isError(zresult) } != 0 {
        return Err(ZstdError::from_message(
            py,
            format!("cannot train dict: {}", zstd_safe::get_error_name(zresult)).as_ref(),
        ));
    }

    // Since the zstd C code writes directly to the buffer, the Vec's internal
    // length wasn't updated. So we need to tell it the new size.
    unsafe {
        dict_data.set_len(zresult);
    }

    let state = RefCell::new(DictState {
        content_type: zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict,
        data: dict_data,
        k: params.k,
        d: params.d,
        cdict: None,
    });

    Ok(ZstdCompressionDict::create_instance(py, state)?.into_object())
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(
        py,
        "ZstdCompressionDict",
        py.get_type::<ZstdCompressionDict>(),
    )?;

    module.add(
        py,
        "train_dictionary",
        py_fn!(
            py,
            train_dictionary(
                dict_size: usize,
                samples: PyObject,
                k: u32 = 0,
                d: u32 = 0,
                f: u32 = 0,
                split_point: f64 = 0.0,
                accel: u32 = 0,
                notifications: u32 = 0,
                dict_id: u32 = 0,
                level: i32 = 0,
                steps: u32 = 0,
                threads: i32 = 0
            )
        ),
    )?;

    Ok(())
}
