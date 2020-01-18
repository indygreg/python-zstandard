#!/usr/bin/env python
# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

from __future__ import print_function

from distutils.version import LooseVersion
import os
import sys
from setuptools import setup

# Need change in 1.10 for ffi.from_buffer() to handle all buffer types
# (like memoryview).
# Need feature in 1.11 for ffi.gc() to declare size of objects so we avoid
# garbage collection pitfalls.
MINIMUM_CFFI_VERSION = "1.11"

try:
    import cffi

    # PyPy (and possibly other distros) have CFFI distributed as part of
    # them. The install_requires for CFFI below won't work. We need to sniff
    # out the CFFI version here and reject CFFI if it is too old.
    cffi_version = LooseVersion(cffi.__version__)
    if cffi_version < LooseVersion(MINIMUM_CFFI_VERSION):
        print(
            "CFFI 1.11 or newer required (%s found); "
            "not building CFFI backend" % cffi_version,
            file=sys.stderr,
        )
        cffi = None

except ImportError:
    cffi = None

import setup_zstd

SUPPORT_LEGACY = False
SYSTEM_ZSTD = False
WARNINGS_AS_ERRORS = False

if os.environ.get("ZSTD_WARNINGS_AS_ERRORS", ""):
    WARNINGS_AS_ERRORS = True

if "--legacy" in sys.argv:
    SUPPORT_LEGACY = True
    sys.argv.remove("--legacy")

if "--system-zstd" in sys.argv:
    SYSTEM_ZSTD = True
    sys.argv.remove("--system-zstd")

if "--warnings-as-errors" in sys.argv:
    WARNINGS_AS_ERRORS = True
    sys.argv.remove("--warning-as-errors")

# Code for obtaining the Extension instance is in its own module to
# facilitate reuse in other projects.
extensions = [
    setup_zstd.get_c_extension(
        name="zstd",
        support_legacy=SUPPORT_LEGACY,
        system_zstd=SYSTEM_ZSTD,
        warnings_as_errors=WARNINGS_AS_ERRORS,
    ),
]

install_requires = []

if cffi:
    import make_cffi

    extensions.append(make_cffi.ffi.distutils_extension())
    install_requires.append("cffi>=%s" % MINIMUM_CFFI_VERSION)

version = None

with open("c-ext/python-zstandard.h", "r") as fh:
    for line in fh:
        if not line.startswith("#define PYTHON_ZSTANDARD_VERSION"):
            continue

        version = line.split()[2][1:-1]
        break

if not version:
    raise Exception(
        "could not resolve package version; " "this should never happen"
    )

setup(
    name="zstandard",
    version=version,
    description="Zstandard bindings for Python",
    long_description=open("README.rst", "r").read(),
    url="https://github.com/indygreg/python-zstandard",
    author="Gregory Szorc",
    author_email="gregory.szorc@gmail.com",
    license="BSD",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: C",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="zstandard zstd compression",
    packages=["zstandard"],
    ext_modules=extensions,
    test_suite="tests",
    install_requires=install_requires,
    tests_require=["hypothesis"],
)
