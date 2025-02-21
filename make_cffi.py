# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

from __future__ import absolute_import

import distutils.ccompiler
import distutils.sysconfig
import os
import re
import subprocess
import tempfile

import cffi
import packaging.tags

HERE = os.path.abspath(os.path.dirname(__file__))

SOURCES = [
    "zstd/zstd.c",
]

# Headers whose preprocessed output will be fed into cdef().
HEADERS = [os.path.join(HERE, "zstd", p) for p in ("zstd_errors.h", "zstd.h", "zdict.h")]

INCLUDE_DIRS = [
    os.path.join(HERE, "zstd"),
]

# cffi can't parse some of the primitives in zstd.h. So we invoke the
# preprocessor and feed its output into cffi.
compiler = distutils.ccompiler.new_compiler()

# Needed for MSVC.
if hasattr(compiler, "initialize"):
    compiler.initialize()

# This performs platform specific customizations, including honoring
# environment variables like CC.
distutils.sysconfig.customize_compiler(compiler)

# Distutils doesn't always set compiler.preprocessor, so invoke the
# preprocessor manually when needed.
args = getattr(compiler, "preprocessor", None)
if compiler.compiler_type == "unix":
    if not args:
        # Using .compiler respects the CC environment variable.
        args = [compiler.compiler[0], "-E"]
    args.extend(
        [
            "-DZSTD_STATIC_LINKING_ONLY",
            "-DZDICT_STATIC_LINKING_ONLY",
        ]
    )
elif compiler.compiler_type == "msvc":
    if not args:
        args = [compiler.cc, "/EP"]
    args.extend(
        [
            "/DZSTD_STATIC_LINKING_ONLY",
            "/DZDICT_STATIC_LINKING_ONLY",
        ]
    )
else:
    raise Exception("unsupported compiler type: %s" % compiler.compiler_type)


def preprocess(path):
    with open(path, "rb") as fh:
        lines = []
        it = iter(fh)

        for line in it:
            # zstd.h includes <stddef.h>, which is also included by cffi's
            # boilerplate. This can lead to duplicate declarations. So we strip
            # this include from the preprocessor invocation.
            #
            # The same things happens for including zstd.h and zstd_errors.h, so
            # give them the same treatment.
            #
            # We define ZSTD_STATIC_LINKING_ONLY, which is redundant with the inline
            # #define in zstdmt_compress.h and results in a compiler warning. So drop
            # the inline #define.
            if line.startswith(
                (
                    b"#include <stddef.h>",
                    b'#include "zstd.h"',
                    b'#include "zstd_errors.h"',
                    b"#define ZSTD_STATIC_LINKING_ONLY",
                )
            ):
                continue

            # There's a naked `static` before the declaration of ZSTD_customMem that
            # confuses the cffi parser. Strip it.
            if line == b'static\n':
                continue

            # The preprocessor environment on Windows doesn't define include
            # paths, so the #include of limits.h fails. We work around this
            # by removing that import and defining INT_MAX ourselves. This is
            # a bit hacky. But it gets the job done.
            # TODO make limits.h work on Windows so we ensure INT_MAX is
            # correct.
            if line.startswith(b"#include <limits.h>"):
                line = b"#define INT_MAX 2147483647\n"

            # ZSTDLIB_API may not be defined if we dropped zstd.h. It isn't
            # important so just filter it out. Ditto for ZSTDLIB_STATIC_API and
            # ZDICTLIB_STATIC_API.
            for prefix in (
                b"ZSTDLIB_API",
                b"ZSTDLIB_STATIC_API",
                b"ZDICTLIB_STATIC_API",
            ):
                if line.startswith(prefix):
                    line = line[len(prefix) :]

            lines.append(line)

    fd, input_file = tempfile.mkstemp(suffix=".h")
    os.write(fd, b"".join(lines))
    os.close(fd)

    try:
        env = dict(os.environ)
        # cffi attempts to decode source as ascii. And the preprocessor
        # may insert non-ascii for some annotations. So try to force
        # ascii output via LC_ALL.
        env["LC_ALL"] = "C"

        if getattr(compiler, "_paths", None):
            env["PATH"] = compiler._paths
        process = subprocess.Popen(
            args + [input_file], stdout=subprocess.PIPE, env=env
        )
        output = process.communicate()[0]
        ret = process.poll()
        if ret:
            raise Exception("preprocessor exited with error")

        return output
    finally:
        os.unlink(input_file)


def normalize_output(output):
    lines = []
    for line in output.splitlines():
        # CFFI's parser doesn't like __attribute__ on UNIX compilers.
        if line.startswith(b'__attribute__ ((visibility ("default"))) '):
            line = line[len(b'__attribute__ ((visibility ("default"))) ') :]

        if line.startswith(b"__attribute__((deprecated"):
            continue
        elif b"__declspec(deprecated(" in line:
            continue
        elif line.startswith(b"__attribute__((__unused__))"):
            continue

        lines.append(line)

    return b"\n".join(lines)

# musl 1.1 doesn't define qsort_r. We need to force using the C90
# variant.
define_macros = []
for tag in packaging.tags.platform_tags():
    if tag.startswith("musllinux_1_1_"):
        define_macros.append(("ZDICT_QSORT", "ZDICT_QSORT_C90"))


ffi = cffi.FFI()
# *_DISABLE_DEPRECATE_WARNINGS prevents the compiler from emitting a warning
# when cffi uses the function. Since we statically link against zstd, even
# if we use the deprecated functions it shouldn't be a huge problem.
ffi.set_source(
    "zstandard._cffi",
    """
#define ZSTD_STATIC_LINKING_ONLY
#define ZSTD_DISABLE_DEPRECATE_WARNINGS
#include <zstd_errors.h>
#include <zstd.h>
#define ZDICT_STATIC_LINKING_ONLY
#define ZDICT_DISABLE_DEPRECATE_WARNINGS
#include <zdict.h>
""",
    sources=SOURCES,
    include_dirs=INCLUDE_DIRS,
    define_macros=define_macros
)

DEFINE = re.compile(rb"^#define\s+([a-zA-Z0-9_]+)\s+(\S+)")

sources = []

# Feed normalized preprocessor output for headers into the cdef parser.
for header in HEADERS:
    preprocessed = preprocess(header)
    sources.append(normalize_output(preprocessed))

    # #define's are effectively erased as part of going through preprocessor.
    # So perform a manual pass to re-add those to the cdef source.
    with open(header, "rb") as fh:
        for line in fh:
            line = line.strip()
            m = DEFINE.match(line)
            if not m:
                continue

            if m.group(1) == b"ZSTD_STATIC_LINKING_ONLY":
                continue

            # The parser doesn't like some constants with complex values.
            if m.group(1) in (b"ZSTD_LIB_VERSION", b"ZSTD_VERSION_STRING"):
                continue

            # These defines create aliases from old (camelCase) type names
            # to the new PascalCase names, which breaks CFFI.
            if m.group(1).lower() == m.group(2).lower():
                continue

            # The ... is magic syntax by the cdef parser to resolve the
            # value at compile time.
            sources.append(b"#define " + m.group(1) + b" ...")

cdeflines = b"\n".join(sources).splitlines()
cdeflines = [line for line in cdeflines if line.strip()]
ffi.cdef(b"\n".join(cdeflines).decode("latin1"))

if __name__ == "__main__":
    ffi.compile()
