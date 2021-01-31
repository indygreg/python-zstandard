// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use {
    crate::{
        compression_parameters::{get_cctx_parameter, int_to_strategy, ZstdCompressionParameters},
        zstd_safe::{CDict, DDict},
        ZstdError,
    },
    pyo3::{
        buffer::PyBuffer,
        exceptions::PyValueError,
        prelude::*,
        types::{PyBytes, PyList},
        wrap_pyfunction,
    },
};

#[pyclass]
pub struct ZstdCompressionDict {
    /// Internal format of dictionary data.
    content_type: zstd_sys::ZSTD_dictContentType_e,

    /// Segment size.
    #[pyo3(get)]
    k: u32,

    /// Dmer size.
    #[pyo3(get)]
    d: u32,

    /// Raw dictionary data.
    ///
    /// Owned by us.
    data: Vec<u8>,

    /// Precomputed compression dictionary.
    cdict: Option<CDict<'static>>,

    /// Precomputed decompression dictionary.
    ddict: Option<DDict<'static>>,
}

impl ZstdCompressionDict {
    pub(crate) fn load_into_cctx(&self, cctx: *mut zstd_sys::ZSTD_CCtx) -> PyResult<()> {
        let zresult = if let Some(cdict) = &self.cdict {
            unsafe { zstd_sys::ZSTD_CCtx_refCDict(cctx, cdict.ptr) }
        } else {
            unsafe {
                zstd_sys::ZSTD_CCtx_loadDictionary_advanced(
                    cctx,
                    self.data.as_ptr() as *const _,
                    self.data.len(),
                    zstd_sys::ZSTD_dictLoadMethod_e::ZSTD_dlm_byRef,
                    self.content_type,
                )
            }
        };

        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            Err(ZstdError::new_err(format!(
                "could not load compression dictionary: {}",
                zstd_safe::get_error_name(zresult)
            )))
        } else {
            Ok(())
        }
    }

    /// Ensure the DDict is populated.
    pub(crate) fn ensure_ddict(&mut self) -> PyResult<()> {
        if self.ddict.is_some() {
            return Ok(());
        }

        let ddict = unsafe {
            zstd_sys::ZSTD_createDDict_advanced(
                self.data.as_ptr() as *const _,
                self.data.len(),
                zstd_sys::ZSTD_dictLoadMethod_e::ZSTD_dlm_byRef,
                self.content_type,
                zstd_sys::ZSTD_customMem {
                    customAlloc: None,
                    customFree: None,
                    opaque: std::ptr::null_mut(),
                },
            )
        };
        if ddict.is_null() {
            return Err(ZstdError::new_err("could not create decompression dict"));
        }

        self.ddict = Some(DDict::from_ptr(ddict));

        Ok(())
    }

    pub(crate) fn load_into_dctx(&mut self, dctx: *mut zstd_sys::ZSTD_DCtx) -> PyResult<()> {
        self.ensure_ddict()?;

        let zresult =
            unsafe { zstd_sys::ZSTD_DCtx_refDDict(dctx, self.ddict.as_ref().unwrap().ptr) };
        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            return Err(ZstdError::new_err(format!(
                "unable to reference prepared dictionary: {}",
                zstd_safe::get_error_name(zresult)
            )));
        }

        Ok(())
    }
}

#[pymethods]
impl ZstdCompressionDict {
    #[new]
    #[args(data, dict_type = "None")]
    fn new(py: Python, buffer: PyBuffer<u8>, dict_type: Option<u32>) -> PyResult<Self> {
        let dict_type = if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto as u32)
        {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto)
        } else if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict as u32) {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict)
        } else if dict_type == Some(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_rawContent as u32) {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_rawContent)
        } else if let Some(value) = dict_type {
            Err(PyValueError::new_err(format!(
                "invalid dictionary load mode: {}; must use DICT_TYPE_* constants",
                value
            )))
        } else {
            Ok(zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto)
        }?;

        let dict_data = buffer.to_vec(py)?;

        Ok(ZstdCompressionDict {
            content_type: dict_type,
            k: 0,
            d: 0,
            data: dict_data,
            cdict: None,
            ddict: None,
        })
    }

    fn __len__(&self) -> usize {
        self.data.len()
    }

    fn as_bytes<'p>(&self, py: Python<'p>) -> PyResult<&'p PyBytes> {
        Ok(PyBytes::new(py, &self.data))
    }

    fn dict_id(&self) -> u32 {
        zstd_safe::get_dict_id(&self.data).unwrap_or(0)
    }

    #[args(level = "None", compression_params = "None")]
    fn precompute_compress(
        &mut self,
        py: Python,
        level: Option<i32>,
        compression_params: Option<Py<ZstdCompressionParameters>>,
    ) -> PyResult<()> {
        let params = if let Some(level) = level {
            if compression_params.is_some() {
                return Err(PyValueError::new_err(
                    "must only specify one of level or compression_params",
                ));
            }

            unsafe { zstd_sys::ZSTD_getCParams(level, 0, self.data.len()) }
        } else if let Some(compression_params) = &compression_params {
            let source_params = compression_params.borrow(py).params;

            let window_log =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_windowLog)?;
            let chain_log =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_chainLog)?;
            let hash_log =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_hashLog)?;
            let search_log =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_searchLog)?;
            let min_match =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_minMatch)?;
            let target_length = get_cctx_parameter(
                source_params,
                zstd_sys::ZSTD_cParameter::ZSTD_c_targetLength,
            )?;
            let strategy =
                get_cctx_parameter(source_params, zstd_sys::ZSTD_cParameter::ZSTD_c_strategy)?;

            zstd_sys::ZSTD_compressionParameters {
                windowLog: window_log as u32,
                chainLog: chain_log as u32,
                hashLog: hash_log as u32,
                searchLog: search_log as u32,
                minMatch: min_match as u32,
                targetLength: target_length as u32,
                strategy: int_to_strategy(strategy as u32)?,
            }
        } else {
            return Err(PyValueError::new_err(
                "must specify one of level or compression_params",
            ));
        };

        let cdict = unsafe {
            zstd_sys::ZSTD_createCDict_advanced(
                self.data.as_ptr() as *const _,
                self.data.len(),
                zstd_sys::ZSTD_dictLoadMethod_e::ZSTD_dlm_byRef,
                self.content_type,
                params,
                zstd_sys::ZSTD_customMem {
                    customAlloc: None,
                    customFree: None,
                    opaque: std::ptr::null_mut(),
                },
            )
        };

        if cdict.is_null() {
            return Err(ZstdError::new_err("unable to precompute dictionary"));
        }

        self.cdict = Some(CDict::from_ptr(cdict));

        Ok(())
    }
}

#[pyfunction(
    dict_size,
    samples,
    k = "0",
    d = "0",
    f = "0",
    split_point = "0.0",
    accel = "0",
    notifications = "0",
    dict_id = "0",
    level = "0",
    steps = "0",
    threads = "0"
)]
fn train_dictionary(
    py: Python,
    dict_size: usize,
    samples: &PyList,
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
) -> PyResult<ZstdCompressionDict> {
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
    for sample in samples.iter() {
        let bytes = sample
            .cast_as::<PyBytes>()
            .or_else(|_| Err(PyValueError::new_err("samples must be bytes")))?;

        samples_len += bytes.as_bytes().len();
    }

    let mut samples_buffer: Vec<u8> = Vec::with_capacity(samples_len);
    let mut sample_sizes: Vec<libc::size_t> = Vec::with_capacity(samples.len());

    for sample in samples.iter() {
        let bytes: &PyBytes = sample.downcast()?;
        let data = bytes.as_bytes();
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
        return Err(ZstdError::new_err(format!(
            "cannot train dict: {}",
            zstd_safe::get_error_name(zresult)
        )));
    }

    // Since the zstd C code writes directly to the buffer, the Vec's internal
    // length wasn't updated. So we need to tell it the new size.
    unsafe {
        dict_data.set_len(zresult);
    }

    Ok(ZstdCompressionDict {
        content_type: zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict,
        k: params.k,
        d: params.d,
        data: dict_data,
        cdict: None,
        ddict: None,
    })
}

pub(crate) fn init_module(module: &PyModule) -> PyResult<()> {
    module.add_class::<ZstdCompressionDict>()?;
    module.add_function(wrap_pyfunction!(train_dictionary, module)?)?;

    Ok(())
}
