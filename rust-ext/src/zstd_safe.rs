// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use std::marker::PhantomData;

/// Safe wrapper for ZSTD_CDict instances.
pub(crate) struct CDict<'a> {
    // TODO don't expose field.
    pub(crate) ptr: *mut zstd_sys::ZSTD_CDict,
    _phantom: PhantomData<&'a ()>,
}

impl<'a> CDict<'a> {
    pub fn from_ptr(ptr: *mut zstd_sys::ZSTD_CDict) -> Self {
        Self {
            ptr,
            _phantom: PhantomData,
        }
    }
}

impl<'a> Drop for CDict<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeCDict(self.ptr);
        }
    }
}

unsafe impl<'a> Send for CDict<'a> {}

unsafe impl<'a> Sync for CDict<'a> {}

/// Safe wrapper for ZSTD_DDict instances.
pub(crate) struct DDict<'a> {
    // TODO don't expose field.
    pub(crate) ptr: *mut zstd_sys::ZSTD_DDict,
    _phantom: PhantomData<&'a ()>,
}

unsafe impl<'a> Send for DDict<'a> {}
unsafe impl<'a> Sync for DDict<'a> {}

impl<'a> Drop for DDict<'a> {
    fn drop(&mut self) {
        unsafe {
            zstd_sys::ZSTD_freeDDict(self.ptr);
        }
    }
}

impl<'a> DDict<'a> {
    pub fn from_ptr(ptr: *mut zstd_sys::ZSTD_DDict) -> Self {
        Self {
            ptr,
            _phantom: PhantomData,
        }
    }
}
