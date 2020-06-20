// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use crate::compression_dict::ZstdCompressionDict;
use crate::compression_parameters::{CCtxParams, ZstdCompressionParameters};
use crate::ZstdError;
use cpython::buffer::PyBuffer;
use cpython::exc::ValueError;
use cpython::{py_class, PyBytes, PyErr, PyModule, PyObject, PyResult, Python, PythonObject};
use std::cell::RefCell;
use std::marker::PhantomData;

pub(crate) struct CCtx<'a>(*mut zstd_sys::ZSTD_CCtx, PhantomData<&'a ()>);

impl<'a> Drop for CCtx<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeCCtx(self.0);
        }
    }
}

unsafe impl<'a> Send for CCtx<'a> {}
unsafe impl<'a> Sync for CCtx<'a> {}

impl<'a> CCtx<'a> {
    fn new() -> Result<Self, &'static str> {
        let cctx = unsafe { zstd_sys::ZSTD_createCCtx() };
        if cctx.is_null() {
            return Err("could not allocate ZSTD_CCtx instance");
        }

        Ok(Self(cctx, PhantomData))
    }

    fn set_parameters(&self, params: &CCtxParams) -> Result<(), String> {
        let zresult = unsafe {
            zstd_sys::ZSTD_CCtx_setParametersUsingCCtxParams(self.0, params.get_raw_ptr())
        };
        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            return Err(zstd_safe::get_error_name(zresult).to_string());
        }

        Ok(())
    }

    pub fn memory_size(&self) -> usize {
        unsafe { zstd_sys::ZSTD_sizeof_CCtx(self.0 as *const _) }
    }

    pub fn reset(&self) -> usize {
        unsafe {
            zstd_sys::ZSTD_CCtx_reset(
                self.0,
                zstd_sys::ZSTD_ResetDirective::ZSTD_reset_session_only,
            )
        }
    }

    pub fn set_pledged_source_size(&self, size: u64) -> Result<(), &'static str> {
        let zresult = unsafe { zstd_sys::ZSTD_CCtx_setPledgedSrcSize(self.0, size) };
        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            Err(zstd_safe::get_error_name(zresult))
        } else {
            Ok(())
        }
    }

    pub fn compress(&self, source: &[u8]) -> Result<Vec<u8>, &'static str> {
        self.reset();

        let dest_len = unsafe { zstd_sys::ZSTD_compressBound(source.len()) };

        let mut dest: Vec<u8> = Vec::with_capacity(dest_len);

        self.set_pledged_source_size(dest_len as _)?;

        let mut in_buffer = zstd_sys::ZSTD_inBuffer {
            src: source.as_ptr() as *const _,
            size: source.len(),
            pos: 0,
        };

        let mut out_buffer = zstd_sys::ZSTD_outBuffer {
            dst: dest.as_mut_ptr() as *mut _,
            size: dest.capacity(),
            pos: 0,
        };

        // By avoiding ZSTD_compress(), we don't necessarily write out content
        // size. This means the parameters to control frame parameters are honored.
        let zresult = unsafe {
            zstd_sys::ZSTD_compressStream2(
                self.0,
                &mut out_buffer as *mut _,
                &mut in_buffer as *mut _,
                zstd_sys::ZSTD_EndDirective::ZSTD_e_end,
            )
        };

        if unsafe { zstd_sys::ZSTD_isError(zresult) } != 0 {
            Err(zstd_safe::get_error_name(zresult))
        } else if zresult > 0 {
            Err("unexpected partial frame flush")
        } else {
            unsafe { dest.set_len(out_buffer.pos) }

            Ok(dest)
        }
    }
}

struct CompressorState<'params, 'cctx> {
    threads: i32,
    dict: Option<ZstdCompressionDict>,
    params: CCtxParams<'params>,
    cctx: CCtx<'cctx>,
}

impl<'params, 'cctx> CompressorState<'params, 'cctx> {
    pub(crate) fn setup_cctx(&self, py: Python) -> PyResult<()> {
        self.cctx
            .set_parameters(&self.params)
            .or_else(|msg| Err(PyErr::new::<ZstdError, _>(py, msg)))?;

        if let Some(dict) = &self.dict {
            dict.load_into_cctx(py, self.cctx.0)?;
        }

        Ok(())
    }
}

py_class!(class ZstdCompressor |py| {
    data state: RefCell<CompressorState<'static, 'static>>;

    def __new__(
        _cls,
        level: i32 = 3,
        dict_data: Option<ZstdCompressionDict> = None,
        compression_params: Option<ZstdCompressionParameters> = None,
        write_checksum: Option<bool> = None,
        write_content_size: Option<bool> = None,
        write_dict_id: Option<bool> = None,
        threads: i32 = 0
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

    def memory_size(&self) -> PyResult<usize> {
        Ok(self.state(py).borrow().cctx.memory_size())
    }

    def compress(&self, data: PyObject) -> PyResult<PyBytes> {
        self.compress_impl(py, data)
    }
});

impl ZstdCompressor {
    fn new_impl(
        py: Python,
        level: i32,
        dict_data: Option<ZstdCompressionDict>,
        compression_params: Option<ZstdCompressionParameters>,
        write_checksum: Option<bool>,
        write_content_size: Option<bool>,
        write_dict_id: Option<bool>,
        threads: i32,
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

        let threads = if threads < 0 {
            num_cpus::get() as i32
        } else {
            threads
        };

        let cctx = CCtx::new().or_else(|msg| Err(PyErr::new::<ZstdError, _>(py, msg)))?;
        let params = CCtxParams::create(py)?;

        if let Some(ref compression_params) = compression_params {
            if write_checksum.is_some() {
                return Err(PyErr::new::<ValueError, _>(
                    py,
                    "cannot define compression_params and write_checksum",
                ));
            }
            if write_content_size.is_some() {
                return Err(PyErr::new::<ValueError, _>(
                    py,
                    "cannot define compression_params and write_content_size",
                ));
            }
            if write_dict_id.is_some() {
                return Err(PyErr::new::<ValueError, _>(
                    py,
                    "cannot define compression_params and write_dict_id",
                ));
            }
            if threads != 0 {
                return Err(PyErr::new::<ValueError, _>(
                    py,
                    "cannot define compression_params and threads",
                ));
            }

            params.apply_compression_parameters(py, compression_params)?;

        // TODO set parameters from CompressionParameters
        } else {
            params.set_parameter(
                py,
                zstd_sys::ZSTD_cParameter::ZSTD_c_compressionLevel,
                level,
            )?;
            params.set_parameter(
                py,
                zstd_sys::ZSTD_cParameter::ZSTD_c_contentSizeFlag,
                if write_content_size.unwrap_or(true) {
                    1
                } else {
                    0
                },
            )?;
            params.set_parameter(
                py,
                zstd_sys::ZSTD_cParameter::ZSTD_c_checksumFlag,
                if write_checksum.unwrap_or(false) {
                    1
                } else {
                    0
                },
            )?;
            params.set_parameter(
                py,
                zstd_sys::ZSTD_cParameter::ZSTD_c_dictIDFlag,
                if write_dict_id.unwrap_or(true) { 1 } else { 0 },
            )?;
            if threads != 0 {
                params.set_parameter(py, zstd_sys::ZSTD_cParameter::ZSTD_c_nbWorkers, threads)?;
            }
        }

        let state = CompressorState {
            threads,
            dict: dict_data,
            params,
            cctx,
        };

        state.setup_cctx(py)?;

        Ok(ZstdCompressor::create_instance(py, RefCell::new(state))?.into_object())
    }

    fn compress_impl(&self, py: Python, data: PyObject) -> PyResult<PyBytes> {
        let state: std::cell::Ref<CompressorState> = self.state(py).borrow();

        let buffer = PyBuffer::get(py, &data)?;

        if !buffer.is_c_contiguous() || buffer.dimensions() > 1 {
            return Err(ZstdError::from_message(
                py,
                "data buffer should be contiguous and have at most one dimension",
            ));
        }

        let source: &[u8] =
            unsafe { std::slice::from_raw_parts(buffer.buf_ptr() as *const _, buffer.len_bytes()) };

        let cctx = &state.cctx;

        // TODO implement 0 copy via Py_SIZE().
        let data = py.allow_threads(|| cctx.compress(source)).or_else(|msg| {
            Err(ZstdError::from_message(
                py,
                format!("cannot compress: {}", msg).as_ref(),
            ))
        })?;

        Ok(PyBytes::new(py, &data))
    }
}

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "ZstdCompressor", py.get_type::<ZstdCompressor>())?;

    Ok(())
}
