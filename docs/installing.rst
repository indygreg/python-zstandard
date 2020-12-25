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

This extension is designed to run with Python 3.5, 3.6, 3.7, 3.8, and 3.9
on common platforms (Linux, Windows, and OS X). On PyPy (both PyPy2 and PyPy3)
we support version 6.0.0 and above. x86 and x86_64 are well-tested on Windows.
Only x86_64 is well-tested on Linux and macOS.

Legacy Format Support
=====================

To enable legacy zstd format support which is needed to handle files compressed
with zstd < 1.0 you need to provide an installation option::

   $ pip install zstandard --install-option="--legacy"

and since pip 7.0 it is possible to have the following line in your
requirements.txt::

   zstandard --install-option="--legacy"
