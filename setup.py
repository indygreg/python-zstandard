#!/usr/bin/env python
# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

from setuptools import setup, Extension

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
    extra_compile_args=[
        '-Izstd',
        '-Izstd/common',
        '-Izstd/compress',
        '-Izstd/decompress',
        '-Izstd/dictBuilder',
    ],
)

setup(
    name='zstandard',
    version='0.0.1',
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
        'Programming Language :: Python :: 3.5',
    ],
    keywords='zstandard zstd compression',
    ext_modules=[ext],
    test_suite='tests',
)
