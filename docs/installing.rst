.. _installing:

==========
Installing
==========

This package is uploaded to PyPI at https://pypi.python.org/pypi/zstandard.
So, to install this package::

   $ pip install zstandard

Binary wheels are made available for some platforms. If you need to
install from a source distribution, all you should need is a working C
compiler and the Python development headers/libraries. On many Linux
distributions, you can install a ``python-dev`` or ``python-devel``
package to provide these dependencies.

Packages are also uploaded to Anaconda Cloud at
https://anaconda.org/indygreg/zstandard. See that URL for how to install
this package with ``conda``.

Requirements
============

This package is designed to run with Python 3.7, 3.8, 3.9, 3.10, and 3.11
on common platforms (Linux, Windows, and OS X). On PyPy (both PyPy2 and PyPy3)
we support version 6.0.0 and above. x86 and x86_64 are well-tested on Windows.
Only x86_64 is well-tested on Linux and macOS.

CFFI Backend
============

In order to build/run the CFFI backend/bindings (as opposed to the C/Rust
backend/bindings), you will need the ``cffi`` package installed. The
``cffi`` package is listed as an optional dependency in ``setup.py`` and
may not get picked up by your packaging tools.

If you wish to use the CFFI backend (or have to use it since your Python
distribution doesn't support compiled extensions using the Python C API -
this is the case for PyPy for example), be sure you have the ``cffi``
package installed.

One way to do this is to depend on the ``zstandard[cffi]`` dependency.
e.g. ``pip install 'zstandard[cffi]'`` or add ``zstandard[cffi]`` to your
pip requirements file.

Legacy Format Support
=====================

To enable legacy zstd format support which is needed to handle files compressed
with zstd < 1.0 you need to provide an installation option::

   $ pip install zstandard --install-option="--legacy"

and since pip 7.0 it is possible to have the following line in your
requirements.txt::

   zstandard --install-option="--legacy"

All Install Arguments
=====================

``setup.py`` accepts the following arguments for influencing behavior:

``--legacy``
   Enable legacy zstd format support in order to read files produced with
   zstd < 1.0.

``--system-zstd``
   Attempt to link against the zstd library present on the system instead
   of the version distributed with the extension.

   The Python extension only supports linking against a specific version of
   zstd. So if the system version differs from what is expected, a build
   or runtime error will result.

``--warning-as-errors``
   Treat all compiler warnings as errors.

``--no-c-backend``
   Do not compile the C-based backend.

``--no-cffi-backend``
   Do not compile the CFFI-based backend.

``--rust-backend``
   Compile the Rust backend (not yet feature complete).

If you invoke ``setup.py``, simply pass the aforementioned arguments. e.g.
``python3.9 setup.py --no-cffi-backend``. If using ``pip``, use the
``--install-option`` argument. e.g.
``python3.9 -m pip install zstandard --install-option --warning-as-errors``.
Or in a pip requirements file: ``zstandard --install-option="--rust-backend"``.

In addition, the following environment variables are recognized:

``ZSTD_EXTRA_COMPILER_ARGS``
   Extra compiler arguments to compile the C backend with.

``ZSTD_WARNINGS_AS_ERRORS``
   Equivalent to ``setup.py --warnings-as-errors``.

Building Against External libzstd
=================================

By default, this package builds and links against a single file ``libzstd``
bundled as part of the package distribution. This copy of ``libzstd`` is
statically linked into the extension.

It is possible to point ``setup.py`` at an external (typically system provided)
``libzstd``. To do this, simply pass ``--system-zstd`` to ``setup.py``. e.g.

``python3.9 setup.py --system-zstd`` or ``python3.9 -m pip install zstandard
--install-option="--system-zstd"``.

When building against a system libzstd, you may need to specify extra compiler
arguments to help Python's build system find the external library. These can
be specified via the ``ZSTD_EXTRA_COMPILER_ARGS`` environment variable. e.g.
``ZSTD_EXTRA_COMPILER_ARGS="-I/usr/local/include" python3.9 setup.py
--system-zstd``.

``python-zstandard`` can be sensitive about what version of ``libzstd`` it links
against. For best results, point this package at the exact same version of
``libzstd`` that it bundles. See the bundled ``zstd/zstd.h`` or
``zstd/zstd.c`` for which version that is.

When linking against an external ``libzstd``, not all package features may be
available. Notably, the ``multi_compress_to_buffer()`` and
``multi_decompress_to_buffer()`` APIs are not available, as these rely on private
symbols in the ``libzstd`` C source code, which require building against private
header files to use.
