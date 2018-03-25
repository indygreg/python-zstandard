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

There is continuous integration for Python versions 2.7, and 3.4+
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
package (1.1.2) only exposed the simple APIs for compression and decompression.
This package exposes much more of the zstd API, including streaming and
dictionary compression. This package also has CFFI support.

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
