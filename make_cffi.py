# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

from __future__ import absolute_import

import cffi
import distutils.ccompiler
import os
import re
import subprocess
import tempfile


HERE = os.path.abspath(os.path.dirname(__file__))

SOURCES = ['zstd/%s' % p for p in (
    'common/entropy_common.c',
    'common/error_private.c',
    'common/fse_decompress.c',
    'common/pool.c',
    'common/threading.c',
    'common/xxhash.c',
    'common/zstd_common.c',
    'compress/fse_compress.c',
    'compress/huf_compress.c',
    'compress/zstd_compress.c',
    'compress/zstd_double_fast.c',
    'compress/zstd_fast.c',
    'compress/zstd_lazy.c',
    'compress/zstd_ldm.c',
    'compress/zstd_opt.c',
    'compress/zstdmt_compress.c',
    'decompress/huf_decompress.c',
    'decompress/zstd_decompress.c',
    'dictBuilder/cover.c',
    'dictBuilder/divsufsort.c',
    'dictBuilder/zdict.c',
)]

# Headers whose preprocessed output will be fed into cdef().
HEADERS = [os.path.join(HERE, 'zstd', *p) for p in (
    ('zstd.h',),
    ('dictBuilder', 'zdict.h'),
)]

INCLUDE_DIRS = [os.path.join(HERE, d) for d in (
    'zstd',
    'zstd/common',
    'zstd/compress',
    'zstd/decompress',
    'zstd/dictBuilder',
)]

# cffi can't parse some of the primitives in zstd.h. So we invoke the
# preprocessor and feed its output into cffi.
compiler = distutils.ccompiler.new_compiler()

# Needed for MSVC.
if hasattr(compiler, 'initialize'):
    compiler.initialize()

# Distutils doesn't set compiler.preprocessor, so invoke the preprocessor
# manually.
if compiler.compiler_type == 'unix':
    args = list(compiler.executables['compiler'])
    args.extend([
        '-E',
        '-DZSTD_STATIC_LINKING_ONLY',
        '-DZDICT_STATIC_LINKING_ONLY',
    ])
elif compiler.compiler_type == 'msvc':
    args = [compiler.cc]
    args.extend([
        '/EP',
        '/DZSTD_STATIC_LINKING_ONLY',
        '/DZDICT_STATIC_LINKING_ONLY',
    ])
else:
    raise Exception('unsupported compiler type: %s' % compiler.compiler_type)

def preprocess(path):
    with open(path, 'rb') as fh:
        lines = []
        it = iter(fh)

        for l in it:
            # zstd.h includes <stddef.h>, which is also included by cffi's
            # boilerplate. This can lead to duplicate declarations. So we strip
            # this include from the preprocessor invocation.
            #
            # The same things happens for including zstd.h, so give it the same
            # treatment.
            #
            # We define ZSTD_STATIC_LINKING_ONLY, which is redundant with the inline
            # #define in zstdmt_compress.h and results in a compiler warning. So drop
            # the inline #define.
            if l.startswith((b'#include <stddef.h>',
                             b'#include "zstd.h"',
                             b'#define ZSTD_STATIC_LINKING_ONLY')):
                continue

            # ZSTDLIB_API may not be defined if we dropped zstd.h. It isn't
            # important so just filter it out.
            if l.startswith(b'ZSTDLIB_API'):
                l = l[len(b'ZSTDLIB_API '):]

            # Some APIs are declared but not implemented. CFFI will generate
            # bindings for them and then complain about a missing symbol at
            # module import time. So we strip out these declarations.
            if l.startswith((b'size_t ZSTD_DCtx_loadDictionary(',
                             b'size_t ZSTD_DCtx_loadDictionary_byReference(',
                             b'size_t ZSTD_DCtx_loadDictionary_advanced(',
                             b'size_t ZSTD_DCtx_refDDict(',
                             b'size_t ZSTD_DCtx_refPrefix(',
                             b'size_t ZSTD_DCtx_refPrefix_advanced(')):
                continue

            lines.append(l)

    fd, input_file = tempfile.mkstemp(suffix='.h')
    os.write(fd, b''.join(lines))
    os.close(fd)

    try:
        process = subprocess.Popen(args + [input_file], stdout=subprocess.PIPE)
        output = process.communicate()[0]
        ret = process.poll()
        if ret:
            raise Exception('preprocessor exited with error')

        return output
    finally:
        os.unlink(input_file)


def normalize_output(output):
    lines = []
    for line in output.splitlines():
        # CFFI's parser doesn't like __attribute__ on UNIX compilers.
        if line.startswith(b'__attribute__ ((visibility ("default"))) '):
            line = line[len(b'__attribute__ ((visibility ("default"))) '):]

        if line.startswith(b'__attribute__((deprecated('):
            continue
        elif b'__declspec(deprecated(' in line:
            continue

        lines.append(line)

    return b'\n'.join(lines)


ffi = cffi.FFI()
# zstd.h uses a possible undefined MIN(). Define it until
# https://github.com/facebook/zstd/issues/976 is fixed.
# *_DISABLE_DEPRECATE_WARNINGS prevents the compiler from emitting a warning
# when cffi uses the function. Since we statically link against zstd, even
# if we use the deprecated functions it shouldn't be a huge problem.
ffi.set_source('_zstd_cffi', '''
#define MIN(a,b) ((a)<(b) ? (a) : (b))
#define ZSTD_STATIC_LINKING_ONLY
#include <zstd.h>
#define ZDICT_STATIC_LINKING_ONLY
#define ZDICT_DISABLE_DEPRECATE_WARNINGS
#include <zdict.h>
''', sources=SOURCES,
     include_dirs=INCLUDE_DIRS,
     extra_compile_args=['-DZSTD_MULTITHREAD'])

DEFINE = re.compile(b'^\\#define ([a-zA-Z0-9_]+) ')

sources = []

# Feed normalized preprocessor output for headers into the cdef parser.
for header in HEADERS:
    preprocessed = preprocess(header)
    sources.append(normalize_output(preprocessed))

    # #define's are effectively erased as part of going through preprocessor.
    # So perform a manual pass to re-add those to the cdef source.
    with open(header, 'rb') as fh:
        for line in fh:
            line = line.strip()
            m = DEFINE.match(line)
            if not m:
                continue

            if m.group(1) == b'ZSTD_STATIC_LINKING_ONLY':
                continue

            # The parser doesn't like some constants with complex values.
            if m.group(1) in (b'ZSTD_LIB_VERSION', b'ZSTD_VERSION_STRING'):
                continue

            # The ... is magic syntax by the cdef parser to resolve the
            # value at compile time.
            sources.append(m.group(0) + b' ...')

cdeflines = b'\n'.join(sources).splitlines()
cdeflines = [l for l in cdeflines if l.strip()]
ffi.cdef(b'\n'.join(cdeflines).decode('latin1'))

if __name__ == '__main__':
    ffi.compile()
