#!/usr/bin/env python
# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

import os
from setuptools import setup, Extension

try:
    import cffi
except ImportError:
    cffi = None


HERE = os.path.abspath(os.path.dirname(__file__))

zstd_sources = ['zstd/%s' % p for p in (
    'common/entropy_common.c',
    'common/fse_decompress.c',
    'common/xxhash.c',
    'common/zstd_common.c',
    'compress/fse_compress.c',
    'compress/huf_compress.c',
    'compress/zbuff_compress.c',
    'compress/zstd_compress.c',
    'decompress/huf_decompress.c',
    'decompress/zbuff_decompress.c',
    'decompress/zstd_decompress.c',
    'dictBuilder/divsufsort.c',
    'dictBuilder/zdict.c',
)]

sources = zstd_sources + ['zstd.c']

# TODO compile with optimizations.

ext = Extension('zstd', sources,
    include_dirs=[os.path.join(HERE, d) for d in (
        'zstd',
        'zstd/common',
        'zstd/compress',
        'zstd/decompress',
        'zstd/dictBuilder',
    )],
)

extensions = [ext]

if cffi:
    import make_cffi
    extensions.append(make_cffi.ffi.distutils_extension())

setup(
    name='zstandard',
    version='0.3.3',
    description='Zstandard bindings for Python',
    long_description=open('README.rst', 'r').read(),
    url='https://github.com/indygreg/python-zstandard',
    author='Gregory Szorc',
    author_email='gregory.szorc@gmail.com',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: C',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='zstandard zstd compression',
    ext_modules=extensions,
    test_suite='tests',
)
