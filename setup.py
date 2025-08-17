#!/usr/bin/env python
# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

from __future__ import print_function

import os
import platform
import sys

from setuptools import setup

# Python 3.12 dropped distutils from the stdlib. Try to access it via
# setuptools.
try:
    from setuptools._distutils.version import LooseVersion
except ImportError:
    from distutils.version import LooseVersion

if sys.version_info[0:2] < (3, 9):
    print("Python 3.9+ is required", file=sys.stderr)
    sys.exit(1)

# Need change in 1.10 for ffi.from_buffer() to handle all buffer types
# (like memoryview).
# Need feature in 1.11 for ffi.gc() to declare size of objects so we avoid
# garbage collection pitfalls.
# Require 1.17 everywhere so we don't have to think about supporting older
# versions.
MINIMUM_CFFI_VERSION = "1.17"

ext_suffix = os.environ.get("SETUPTOOLS_EXT_SUFFIX")
if ext_suffix:
    import sysconfig

    # setuptools._distutils.command.build_ext doesn't use
    # SETUPTOOLS_EXT_SUFFIX like setuptools.command.build_ext does.
    # Work around the issue so that cross-compilation can work
    # properly.
    sysconfig.get_config_vars()["EXT_SUFFIX"] = ext_suffix
    try:
        # Older versions of python didn't have EXT_SUFFIX, and setuptools
        # sets its own value, but since we've already set one, we don't
        # want setuptools to overwrite it.
        import setuptools._distutils.compat.py39 as py39compat
    except ImportError:
        try:
            import setuptools._distutils.py39compat as py39compat
        except ImportError:
            pass
    if py39compat:
        py39compat.add_ext_suffix = lambda vars: None

try:
    import cffi

    # PyPy (and possibly other distros) have CFFI distributed as part of
    # them.
    cffi_version = LooseVersion(cffi.__version__)
    if cffi_version < LooseVersion(MINIMUM_CFFI_VERSION):
        print(
            "CFFI %s or newer required (%s found); "
            "not building CFFI backend" % (MINIMUM_CFFI_VERSION, cffi_version),
            file=sys.stderr,
        )
        cffi = None

except ImportError:
    cffi = None

sys.path.insert(0, ".")

import setup_zstd  # noqa: E402

SUPPORT_LEGACY = False
SYSTEM_ZSTD = False
WARNINGS_AS_ERRORS = False
C_BACKEND = True
CFFI_BACKEND = True
RUST_BACKEND = False

if os.environ.get("ZSTD_WARNINGS_AS_ERRORS", ""):
    WARNINGS_AS_ERRORS = True

# PyPy doesn't support the C backend.
if platform.python_implementation() == "PyPy":
    C_BACKEND = False

if "--legacy" in sys.argv:
    SUPPORT_LEGACY = True
    sys.argv.remove("--legacy")

if "--system-zstd" in sys.argv:
    SYSTEM_ZSTD = True
    sys.argv.remove("--system-zstd")

if "--warnings-as-errors" in sys.argv:
    WARNINGS_AS_ERRORS = True
    sys.argv.remove("--warning-as-errors")

if "--no-c-backend" in sys.argv:
    C_BACKEND = False
    sys.argv.remove("--no-c-backend")

if "--no-cffi-backend" in sys.argv:
    CFFI_BACKEND = False
    sys.argv.remove("--no-cffi-backend")

if "--rust-backend" in sys.argv:
    RUST_BACKEND = True
    sys.argv.remove("--rust-backend")

# Code for obtaining the Extension instance is in its own module to
# facilitate reuse in other projects.
extensions = []

if C_BACKEND:
    extensions.append(
        setup_zstd.get_c_extension(
            support_legacy=SUPPORT_LEGACY,
            system_zstd=SYSTEM_ZSTD,
            warnings_as_errors=WARNINGS_AS_ERRORS,
        )
    )

if RUST_BACKEND:
    extensions.append(setup_zstd.get_rust_extension())

if CFFI_BACKEND and cffi:
    import make_cffi

    extensions.append(make_cffi.ffi.distutils_extension())

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
    packages=["zstandard"],
    package_data={"zstandard": ["__init__.pyi", "py.typed"]},
    ext_modules=extensions,
    cmdclass={"build_ext": setup_zstd.RustBuildExt},
    test_suite="tests",
    tests_require=["hypothesis"],
)
