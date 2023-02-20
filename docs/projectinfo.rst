===================
Project Information
===================

State of Project
================

The project is officially in beta state. The author is reasonably satisfied
that functionality works as advertised. **There will be some backwards
incompatible changes before 1.0, probably in the 0.9 release.** This may
involve renaming the main module from *zstd* to *zstandard* and renaming
various types and methods. Pin the package version to prevent unwanted
breakage when this change occurs!

This project is vendored and distributed with Mercurial 4.1, where it is
used in a production capacity.

There is continuous integration for Python versions and 3.7+
on Linux x86_x64 and Windows x86 and x86_64. The author is reasonably
confident the extension is stable and works as advertised on these
platforms.

The CFFI bindings are mostly feature complete. Where a feature is implemented
in CFFI, unit tests run against both C extension and CFFI implementation to
ensure behavior parity.

Comparison to Other Python Bindings
===================================

https://pypi.python.org/pypi/zstd is an alternate Python binding to
Zstandard. At the time this was written, the latest release of that
package (1.4.8) only exposed the simple APIs for compression and decompression.
This package exposes much more of the zstd API, including streaming and
dictionary compression. This package also has CFFI support.

https://github.com/animalize/pyzstd is an alternate Python binding to
Zstandard. At the time this was written, the latest release of that
package (0.14.1) exposed a fraction of the functionality in this
package. There may be some minor features in ``pyzstd`` not found in
this package. But those features could be added easily if someone made
a feature request. Also, ``pyzstd`` lacks CFFI support, so it won't run
on PyPy.

Performance
===========

zstandard is a highly tunable compression algorithm. In its default settings
(compression level 3), it will be faster at compression and decompression and
will have better compression ratios than zlib on most data sets. When tuned
for speed, it approaches lz4's speed and ratios. When tuned for compression
ratio, it approaches lzma ratios and compression speed, but decompression
speed is much faster. See the official zstandard documentation for more.

zstandard and this library support multi-threaded compression. There is a
mechanism to compress large inputs using multiple threads.

The performance of this library is usually very similar to what the zstandard
C API can deliver. Overhead in this library is due to general Python overhead
and can't easily be avoided by *any* zstandard Python binding. This library
exposes multiple APIs for performing compression and decompression so callers
can pick an API suitable for their need. Contrast with the compression
modules in Python's standard library (like ``zlib``), which only offer limited
mechanisms for performing operations. The API flexibility means consumers can
choose to use APIs that facilitate zero copying or minimize Python object
creation and garbage collection overhead.

This library is capable of single-threaded throughputs well over 1 GB/s. For
exact numbers, measure yourself. The source code repository has a ``bench.py``
script that can be used to measure things.

Bundling of Zstandard Source Code
=================================

The source repository for this project contains a vendored copy of the
Zstandard source code. This is done for a few reasons.

First, Zstandard is relatively new and not yet widely available as a system
package. Providing a copy of the source code enables the Python C extension
to be compiled without requiring the user to obtain the Zstandard source code
separately.

Second, Zstandard has both a stable *public* API and an *experimental* API.
The *experimental* API is actually quite useful (contains functionality for
training dictionaries for example), so it is something we wish to expose to
Python. However, the *experimental* API is only available via static linking.
Furthermore, the *experimental* API can change at any time. So, control over
the exact version of the Zstandard library linked against is important to
ensure known behavior.

Note on Zstandard's *Experimental* API
======================================

Many of the Zstandard APIs used by this module are marked as *experimental*
within the Zstandard project.

It is unclear how Zstandard's C API will evolve over time, especially with
regards to this *experimental* functionality. We will try to maintain
backwards compatibility at the Python API level. However, we cannot
guarantee this for things not under our control.

Since a copy of the Zstandard source code is distributed with this
module and since we compile against it, the behavior of a specific
version of this module should be constant for all of time. So if you
pin the version of this module used in your projects (which is a Python
best practice), you should be shielded from unwanted future changes.

Donate
======

A lot of time has been invested into this project by the author.

If you find this project useful and would like to thank the author for
their work or commission a feature, consider donating some money.
Any amount is appreciated. This can be done through GitHub Sponsors at
https://github.com/sponsors/indygreg.
