# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

import distutils.ccompiler
import os

from distutils.extension import Extension


zstd_sources = [
    "zstd/%s" % p
    for p in (
        "common/debug.c",
        "common/entropy_common.c",
        "common/error_private.c",
        "common/fse_decompress.c",
        "common/pool.c",
        "common/threading.c",
        "common/xxhash.c",
        "common/zstd_common.c",
        "compress/fse_compress.c",
        "compress/hist.c",
        "compress/huf_compress.c",
        "compress/zstd_compress_literals.c",
        "compress/zstd_compress_sequences.c",
        "compress/zstd_compress.c",
        "compress/zstd_double_fast.c",
        "compress/zstd_fast.c",
        "compress/zstd_lazy.c",
        "compress/zstd_ldm.c",
        "compress/zstd_opt.c",
        "compress/zstdmt_compress.c",
        "decompress/huf_decompress.c",
        "decompress/zstd_ddict.c",
        "decompress/zstd_decompress.c",
        "decompress/zstd_decompress_block.c",
        "dictBuilder/cover.c",
        "dictBuilder/divsufsort.c",
        "dictBuilder/fastcover.c",
        "dictBuilder/zdict.c",
    )
]

zstd_sources_legacy = [
    "zstd/%s" % p
    for p in (
        "deprecated/zbuff_common.c",
        "deprecated/zbuff_compress.c",
        "deprecated/zbuff_decompress.c",
        "legacy/zstd_v01.c",
        "legacy/zstd_v02.c",
        "legacy/zstd_v03.c",
        "legacy/zstd_v04.c",
        "legacy/zstd_v05.c",
        "legacy/zstd_v06.c",
        "legacy/zstd_v07.c",
    )
]

zstd_includes = [
    "zstd",
    "zstd/common",
    "zstd/compress",
    "zstd/decompress",
    "zstd/dictBuilder",
]

zstd_includes_legacy = [
    "zstd/deprecated",
    "zstd/legacy",
]

ext_includes = [
    "c-ext",
    "zstd/common",
]

ext_sources = [
    "zstd/common/error_private.c",
    "zstd/common/pool.c",
    "zstd/common/threading.c",
    "zstd/common/zstd_common.c",
    "zstd.c",
    "c-ext/bufferutil.c",
    "c-ext/compressiondict.c",
    "c-ext/compressobj.c",
    "c-ext/compressor.c",
    "c-ext/compressoriterator.c",
    "c-ext/compressionchunker.c",
    "c-ext/compressionparams.c",
    "c-ext/compressionreader.c",
    "c-ext/compressionwriter.c",
    "c-ext/constants.c",
    "c-ext/decompressobj.c",
    "c-ext/decompressor.c",
    "c-ext/decompressoriterator.c",
    "c-ext/decompressionreader.c",
    "c-ext/decompressionwriter.c",
    "c-ext/frameparams.c",
]

zstd_depends = [
    "c-ext/python-zstandard.h",
]


def get_c_extension(
    support_legacy=False,
    system_zstd=False,
    name="zstd",
    warnings_as_errors=False,
    root=None,
):
    """Obtain a distutils.extension.Extension for the C extension.

    ``support_legacy`` controls whether to compile in legacy zstd format support.

    ``system_zstd`` controls whether to compile against the system zstd library.
    For this to work, the system zstd library and headers must match what
    python-zstandard is coded against exactly.

    ``name`` is the module name of the C extension to produce.

    ``warnings_as_errors`` controls whether compiler warnings are turned into
    compiler errors.

    ``root`` defines a root path that source should be computed as relative
    to. This should be the directory with the main ``setup.py`` that is
    being invoked. If not defined, paths will be relative to this file.
    """
    actual_root = os.path.abspath(os.path.dirname(__file__))
    root = root or actual_root

    sources = set([os.path.join(actual_root, p) for p in ext_sources])
    if not system_zstd:
        sources.update([os.path.join(actual_root, p) for p in zstd_sources])
        if support_legacy:
            sources.update(
                [os.path.join(actual_root, p) for p in zstd_sources_legacy]
            )
    sources = list(sources)

    include_dirs = set([os.path.join(actual_root, d) for d in ext_includes])
    if not system_zstd:
        include_dirs.update(
            [os.path.join(actual_root, d) for d in zstd_includes]
        )
        if support_legacy:
            include_dirs.update(
                [os.path.join(actual_root, d) for d in zstd_includes_legacy]
            )
    include_dirs = list(include_dirs)

    depends = [os.path.join(actual_root, p) for p in zstd_depends]

    compiler = distutils.ccompiler.new_compiler()

    # Needed for MSVC.
    if hasattr(compiler, "initialize"):
        compiler.initialize()

    if compiler.compiler_type == "unix":
        compiler_type = "unix"
    elif compiler.compiler_type == "msvc":
        compiler_type = "msvc"
    elif compiler.compiler_type == "mingw32":
        compiler_type = "mingw32"
    else:
        raise Exception("unhandled compiler type: %s" % compiler.compiler_type)

    extra_args = ["-DZSTD_MULTITHREAD"]

    if not system_zstd:
        extra_args.append("-DZSTDLIB_VISIBILITY=")
        extra_args.append("-DZDICTLIB_VISIBILITY=")
        extra_args.append("-DZSTDERRORLIB_VISIBILITY=")

        if compiler_type == "unix":
            extra_args.append("-fvisibility=hidden")

    if not system_zstd and support_legacy:
        extra_args.append("-DZSTD_LEGACY_SUPPORT=1")

    if warnings_as_errors:
        if compiler_type in ("unix", "mingw32"):
            extra_args.append("-Werror")
        elif compiler_type == "msvc":
            extra_args.append("/WX")
        else:
            assert False

    libraries = ["zstd"] if system_zstd else []

    # Python 3.7 doesn't like absolute paths. So normalize to relative.
    sources = [os.path.relpath(p, root) for p in sources]
    include_dirs = [os.path.relpath(p, root) for p in include_dirs]
    depends = [os.path.relpath(p, root) for p in depends]

    # TODO compile with optimizations.
    return Extension(
        name,
        sources,
        include_dirs=include_dirs,
        depends=depends,
        extra_compile_args=extra_args,
        libraries=libraries,
    )
