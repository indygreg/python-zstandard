// Copyright (c) 2020-present, Gregory Szorc
// All rights reserved.
//
// This software may be modified and distributed under the terms
// of the BSD license. See the LICENSE file for details.

use cpython::{PyBytes, PyModule, PyResult, Python};

pub(crate) const COMPRESSOBJ_FLUSH_FINISH: i32 = 0;
pub(crate) const COMPRESSOBJ_FLUSH_BLOCK: i32 = 1;

pub(crate) fn init_module(py: Python, module: &PyModule) -> PyResult<()> {
    module.add(py, "__version", super::VERSION)?;
    module.add(py, "__doc__", "Rust backend for zstandard bindings")?;

    module.add(py, "FLUSH_BLOCK", 0)?;
    module.add(py, "FLUSH_FRAME", 1)?;

    module.add(py, "COMPRESSOBJ_FLUSH_FINISH", COMPRESSOBJ_FLUSH_FINISH)?;
    module.add(py, "COMPRESSOBJ_FLUSH_BLOCK", COMPRESSOBJ_FLUSH_BLOCK)?;

    module.add(
        py,
        "ZSTD_VERSION",
        (
            zstd_safe::VERSION_MAJOR,
            zstd_safe::VERSION_MINOR,
            zstd_safe::VERSION_RELEASE,
        ),
    )?;
    module.add(py, "FRAME_HEADER", PyBytes::new(py, b"\x28\xb5\x2f\xfd"))?;

    module.add(py, "CONTENTSIZE_UNKNOWN", zstd_safe::CONTENTSIZE_UNKNOWN)?;
    module.add(py, "CONTENTSIZE_ERROR", zstd_safe::CONTENTSIZE_ERROR)?;

    module.add(py, "MAX_COMPRESSION_LEVEL", zstd_safe::max_c_level())?;
    module.add(
        py,
        "COMPRESSION_RECOMMENDED_INPUT_SIZE",
        zstd_safe::cstream_in_size(),
    )?;
    module.add(
        py,
        "COMPRESSION_RECOMMENDED_OUTPUT_SIZE",
        zstd_safe::cstream_out_size(),
    )?;
    module.add(
        py,
        "DECOMPRESSION_RECOMMENDED_INPUT_SIZE",
        zstd_safe::dstream_in_size(),
    )?;
    module.add(
        py,
        "DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE",
        zstd_safe::dstream_out_size(),
    )?;

    module.add(py, "MAGIC_NUMBER", zstd_safe::MAGICNUMBER)?;
    module.add(py, "BLOCKSIZELOG_MAX", zstd_safe::BLOCKSIZELOG_MAX)?;
    module.add(py, "BLOCKSIZE_MAX", zstd_safe::BLOCKSIZE_MAX)?;
    module.add(py, "WINDOWLOG_MIN", zstd_safe::WINDOWLOG_MIN)?;

    let windowlog_max = if cfg!(target_pointer_width = "32") {
        zstd_safe::WINDOWLOG_MAX_32
    } else {
        zstd_safe::WINDOWLOG_MAX_64
    };

    module.add(py, "WINDOWLOG_MAX", windowlog_max)?;
    module.add(py, "CHAINLOG_MIN", zstd_safe::CHAINLOG_MIN)?;
    module.add(
        py,
        "CHAINLOG_MAX",
        if cfg!(target_pointer_width = "32") {
            zstd_safe::CHAINLOG_MAX_32
        } else {
            zstd_safe::CHAINLOG_MAX_64
        },
    )?;
    module.add(py, "HASHLOG_MIN", zstd_safe::HASHLOG_MIN)?;
    module.add(
        py,
        "HASHLOG_MAX",
        if windowlog_max < 30 {
            windowlog_max
        } else {
            30
        },
    )?;
    module.add(py, "HASHLOG3_MAX", zstd_safe::HASHLOG3_MAX)?;
    module.add(py, "SEARCHLOG_MIN", zstd_safe::SEARCHLOG_MIN)?;
    module.add(py, "SEARCHLOG_MAX", windowlog_max - 1)?;
    module.add(py, "MINMATCH_MIN", zstd_sys::ZSTD_MINMATCH_MIN)?;
    module.add(py, "MINMATCH_MAX", zstd_sys::ZSTD_MINMATCH_MAX)?;
    // TODO SEARCHLENGTH_* is deprecated.
    module.add(py, "SEARCHLENGTH_MIN", zstd_sys::ZSTD_MINMATCH_MIN)?;
    module.add(py, "SEARCHLENGTH_MAX", zstd_sys::ZSTD_MINMATCH_MAX)?;
    module.add(py, "TARGETLENGTH_MIN", zstd_safe::TARGETLENGTH_MIN)?;
    module.add(py, "TARGETLENGTH_MAX", zstd_safe::TARGETLENGTH_MAX)?;
    module.add(py, "LDM_MINMATCH_MIN", zstd_safe::LDM_MINMATCH_MIN)?;
    module.add(py, "LDM_MINMATCH_MAX", zstd_safe::LDM_MINMATCH_MAX)?;
    module.add(
        py,
        "LDM_BUCKETSIZELOG_MAX",
        zstd_safe::LDM_BUCKETSIZELOG_MAX,
    )?;

    module.add(py, "STRATEGY_FAST", zstd_safe::Strategy::ZSTD_fast as u32)?;
    module.add(py, "STRATEGY_DFAST", zstd_safe::Strategy::ZSTD_dfast as u32)?;
    module.add(
        py,
        "STRATEGY_GREEDY",
        zstd_safe::Strategy::ZSTD_greedy as u32,
    )?;
    module.add(py, "STRATEGY_LAZY", zstd_safe::Strategy::ZSTD_lazy as u32)?;
    module.add(py, "STRATEGY_LAZY2", zstd_safe::Strategy::ZSTD_lazy2 as u32)?;
    module.add(
        py,
        "STRATEGY_BTLAZY2",
        zstd_safe::Strategy::ZSTD_btlazy2 as u32,
    )?;
    module.add(py, "STRATEGY_BTOPT", zstd_safe::Strategy::ZSTD_btopt as u32)?;
    module.add(
        py,
        "STRATEGY_BTULTRA",
        zstd_safe::Strategy::ZSTD_btultra as u32,
    )?;
    module.add(
        py,
        "STRATEGY_BTULTRA2",
        zstd_safe::Strategy::ZSTD_btultra2 as u32,
    )?;

    module.add(
        py,
        "DICT_TYPE_AUTO",
        zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_auto as u32,
    )?;
    module.add(
        py,
        "DICT_TYPE_RAWCONTENT",
        zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_rawContent as u32,
    )?;
    module.add(
        py,
        "DICT_TYPE_FULLDICT",
        zstd_sys::ZSTD_dictContentType_e::ZSTD_dct_fullDict as u32,
    )?;

    module.add(
        py,
        "FORMAT_ZSTD1",
        zstd_sys::ZSTD_format_e::ZSTD_f_zstd1 as u32,
    )?;
    module.add(
        py,
        "FORMAT_ZSTD1_MAGICLESS",
        zstd_sys::ZSTD_format_e::ZSTD_f_zstd1_magicless as u32,
    )?;

    Ok(())
}
