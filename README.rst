================
python-zstandard
================

This project provides a Python C extension for interfacing with the
`Zstandard <http://www.zstd.net>`_ compression library.

The primary goal of the extension is to provide a Pythonic interface to
the underlying C API. This means exposing most of the features and flexibility
of the C API while not sacrificing usability or safety that Python provides.

.. image:: https://travis-ci.org/indygreg/python-zstandard.svg?branch=master
    :target: https://travis-ci.org/indygreg/python-zstandard

State of Project
================

The project is still in alpha state.

Implemented functionality should work. However, the code hasn't undergone
a rigorous audit for memory leaks, common mistakes in Python C extensions,
etc. If good inputs are used, things should work. If bad inputs are used,
crashes may occur.

The API is also not guaranteed to be stable. Expect changes.

Requirements
============

This extension is designed to run with Python 2.6, 2.7, 3.3, 3.4, and 3.5.
However, not all versions may run while the project is in alpha state.

Comparison to Other Python Bindings
===================================

https://pypi.python.org/pypi/zstd is an alternative Python binding to
Zstandard. At the time this was written, the latest release of that
package (1.0.0.2) had the following significant differences from this package:

* It only exposes the simple API for compression and decompression operations.
  This extension exposes the streaming API, dictionary training, and more.
* It adds a custom framing header to compressed data and there is no way to
  disable it. This means that data produced with that module cannot be used by
  other Zstandard implementations.

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

Instructions for Building and Testing
=====================================

Once you have the source code, the extension can be built via setup.py::

   $ python setup.py build_ext

To test, use your Python test runner of choice on the ``tests`` directory::

   $ python -m unittest discover

API
===

The compiled C extension provides a ``zstd`` Python module. This module
exposes the following interfaces.

Streaming Compression
---------------------

The preferred mechanism to compress and decompress data involves *streaming*
data into a function one chunk at a time. This approach is advantageous
because it establishes an upper bound on memory usage.

The current implementation of streaming relies on a *writer* pattern. A
*writer* is an object that exposes a ``write(data)`` method. This method
will be called periodically with the output data. File objects and various
other built-in Python types (such as ``io.BytesIO``) provide such an interface.

Here is an example showing how to stream data into a compressor::

    with open(input_path, 'rb') as ifh:
        with open(output_path, 'wb') as ofh:
            with zstd.compresswriter(ofh) as compressor:
                while True:
                     chunk = ifh.read(8192)
                     if not chunk:
                         break

                    compressor.compress(chunk)

And here is the same thing going in reverse::

    with open(input_path, 'rb') as ifh:
        with open(output_path, 'wb') as ofh:
            with zstd.decompresswriter(ofh) as decompressor:
                while True:
                    chunk = ifh.read(8192)
                    if not chunk:
                        break

                    decompressor.decompress(chunk)

Simple Compression
------------------

A simple API is provided to turn input bytes into compressed output bytes::

    compress(data[, level])

This is a one-shot API: the entirety of the input data will be consumed
and returned as compressed bytes.

**When compressing large amounts of data, it is recommended to use streaming
compression, as it avoids large allocations necessary to hold the input and
output buffers.**

Misc Functionality
==================

ZSTD_VERSION
    This module attribute exposes a 3-tuple of the Zstandard version. e.g.
    ``(1, 0, 0)``.

Experimental API
================

The functionality described in this section comes from the Zstandard
*experimental* API. As such, it may change as the bundled Zstandard release
is updated.

**Use this functionality at your own risk, as its API may change with
future releases of this C extension.** It is highly recommended to pin the
version of this extension in your Python projects to guard against unwanted
changes.

Constants
---------

The following constants are exposed:

MAX_COMPRESSION_LEVEL
    Integer max compression level accepted by compression functions
COMPRESSION_RECOMMENDED_INPUT_SIZE
    Recommended chunk size to feed to compressor functions
COMPRESSION_RECOMMENDED_OUTPUT_SIZE
    Recommended chunk size for compression output
DECOMPRESSION_RECOMMENDED_INPUT_SIZE
    Recommended chunk size to feed into decompresor functions
DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE
    Recommended chunk size for decompression output

MAGIC_NUMBER
    Frame header
WINDOWLOG_MIN
    Minimum value for compression parameter
WINDOWLOG_MAX
    Maximum value for compression parameter
CHAINLOG_MIN
    Minimum value for compression parameter
CHAINLOG_MAX
    Maximum value for compression parameter
HASHLOG_MIN
    Minimum value for compression parameter
HASHLOG_MAX
    Maximum value for compression parameter
SEARCHLOG_MIN
    Minimum value for compression parameter
SEARCHLOG_MAX
    Maximum value for compression parameter
SEARCHLENGTH_MIN
    Minimum value for compression parameter
SEARCHLENGTH_MAX
    Maximum value for compression parameter
TARGETLENGTH_MIN
    Minimum value for compression parameter
TARGETLENGTH_MAX
    Maximum value for compression parameter
STRATEGY_FAST
    Compression strategory
STRATEGY_DFAST
    Compression strategory
STRATEGY_GREEDY
    Compression strategory
STRATEGY_LAZY
    Compression strategory
STRATEGY_LAZY2
    Compression strategory
STRATEGY_BTLAZY2
    Compression strategory
STRATEGY_BTOPT
    Compression strategory

Structs
-------

CompressionParameters
^^^^^^^^^^^^^^^^^^^^^

This struct provides advanced control over compression. This can be specified
instead of a compression level to adjust how compression behaves.

FrameParameters
^^^^^^^^^^^^^^^

This struct controls the behavior of Zstandards framing protocol.

Functions
---------

estimate_compression_context_size(CompressionParameters)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Given a ``CompressionParameters`` struct, estimate the memory size required
to perform compression.

get_compression_parameters(compression_level[, source_size[, dict_size]])
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Obtain a ``CompressionParameters`` struct given an integer compression level and
optional input and dictionary sizes.

train_dictionary(size, samples)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Train a compression dictionary on samples, which must be a list of bytes
instances.

Returns binary data constituting the dictionary. The dictionary will be at
most ``size`` bytes long.

dictionary_id(data)
^^^^^^^^^^^^^^^^^^^

Given raw data of a compression dictionary, return its integer ID.

Using Dictionaries for Compression and Decompression
----------------------------------------------------

It is possible to pass dictionary data to a compressor and decompressor.
For example::

    d = zstd.train_dictionary(16384, samples)
    buffer = io.BytesIO()
    with zstd.compresswriter(buffer, dict_data=d) as compressor:
        compressor.compress(data_to_compress_with_dictionary)

    buffer = io.BytesIO()
    with zstd.decompresswriter(buffer, dict_data=d) as decompressor:
        decompressor.decompress(data_to_decompress_with_dictionary)

Explicit Compression Parameters
-------------------------------

Zstandard's integer compression levels along with the input size and dictionary
size are converted into a data structure defining multiple parameters to tune
behavior of the compression algorithm. It is possible to use define this
data structure explicitly to have fine control over the compression algorithm.

The ``zstd.CompressionParameters`` named tuple represents this data structure.
You can see how Zstandard converts compression levels to this data structure
by calling ``zstd.get_compression_parameters()``. e.g.::

    zstd.get_compression_parameters(5)

You can also construct compression parameters from their low-level components::

    params = zstd.CompressionParameters(20, 6, 12, 5, 4, 10, zstd.STRATEGY_FAST)

(You'll likely want to read the Zstandard source code for what these parameters
do.)

You can then configure a compressor to use the custom parameters::

    with zstd.compresswriter(writer, compression_params=params) as compressor:
        ...
