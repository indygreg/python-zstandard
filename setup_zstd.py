# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

import distutils.ccompiler
import distutils.command.build_ext
import distutils.extension
import os
import shutil
import subprocess
import sys


zstd_sources = [
    "zstd/common/debug.c",
    "zstd/common/entropy_common.c",
    "zstd/common/error_private.c",
    "zstd/common/fse_decompress.c",
    "zstd/common/pool.c",
    "zstd/common/threading.c",
    "zstd/common/xxhash.c",
    "zstd/common/zstd_common.c",
    "zstd/compress/fse_compress.c",
    "zstd/compress/hist.c",
    "zstd/compress/huf_compress.c",
    "zstd/compress/zstd_compress_literals.c",
    "zstd/compress/zstd_compress_sequences.c",
    "zstd/compress/zstd_compress_superblock.c",
    "zstd/compress/zstd_compress.c",
    "zstd/compress/zstd_double_fast.c",
    "zstd/compress/zstd_fast.c",
    "zstd/compress/zstd_lazy.c",
    "zstd/compress/zstd_ldm.c",
    "zstd/compress/zstd_opt.c",
    "zstd/compress/zstdmt_compress.c",
    "zstd/decompress/huf_decompress.c",
    "zstd/decompress/zstd_ddict.c",
    "zstd/decompress/zstd_decompress.c",
    "zstd/decompress/zstd_decompress_block.c",
    "zstd/dictBuilder/cover.c",
    "zstd/dictBuilder/divsufsort.c",
    "zstd/dictBuilder/fastcover.c",
    "zstd/dictBuilder/zdict.c",
]

zstd_sources_legacy = [
    "zstd/deprecated/zbuff_common.c",
    "zstd/deprecated/zbuff_compress.c",
    "zstd/deprecated/zbuff_decompress.c",
    "zstd/legacy/zstd_v01.c",
    "zstd/legacy/zstd_v02.c",
    "zstd/legacy/zstd_v03.c",
    "zstd/legacy/zstd_v04.c",
    "zstd/legacy/zstd_v05.c",
    "zstd/legacy/zstd_v06.c",
    "zstd/legacy/zstd_v07.c",
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
]

zstd_depends = [
    "c-ext/python-zstandard.h",
    "c-ext/pythoncapi_compat.h",
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
    sources = sorted(sources)

    include_dirs = set([os.path.join(actual_root, d) for d in ext_includes])
    if not system_zstd:
        include_dirs.update(
            [os.path.join(actual_root, d) for d in zstd_includes]
        )
        if support_legacy:
            include_dirs.update(
                [os.path.join(actual_root, d) for d in zstd_includes_legacy]
            )
    include_dirs = sorted(include_dirs)

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
    return distutils.extension.Extension(
        name,
        sources,
        include_dirs=include_dirs,
        depends=depends,
        extra_compile_args=extra_args,
        libraries=libraries,
    )


class RustExtension(distutils.extension.Extension):
    def __init__(self, name, root):
        super().__init__(name, [])

        self.root = root

        self.depends.extend(
            [
                os.path.join(root, "Cargo.toml"),
                os.path.join(root, "rust-ext", "src", "lib.rs"),
            ]
        )

    def build(self, build_dir, get_ext_path_fn):
        env = os.environ.copy()
        env["PYTHON_SYS_EXECUTABLE"] = sys.executable

        args = [
            "cargo",
            "build",
            "--release",
            "--target-dir",
            str(build_dir),
        ]

        subprocess.run(args, env=env, cwd=self.root, check=True)

        dest_path = get_ext_path_fn(self.name)

        if os.name == "nt":
            rust_lib_filename = "%s.dll" % self.name
        elif sys.platform == "darwin":
            rust_lib_filename = "lib%s.dylib" % self.name
        else:
            rust_lib_filename = "lib%s.so" % self.name

        rust_lib = os.path.join(build_dir, "release", rust_lib_filename)
        os.makedirs(os.path.dirname(rust_lib), exist_ok=True)

        shutil.copy2(rust_lib, dest_path)


class RustBuildExt(distutils.command.build_ext.build_ext):
    def build_extension(self, ext):
        if isinstance(ext, RustExtension):
            ext.build(
                build_dir=os.path.abspath(self.build_temp),
                get_ext_path_fn=self.get_ext_fullpath,
            )
        else:
            super().build_extension(ext)


def get_rust_extension(root=None,):
    actual_root = os.path.abspath(os.path.dirname(__file__))
    root = root or actual_root

    return RustExtension("zstandard_oxidized", root)
