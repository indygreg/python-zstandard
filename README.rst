================
python-zstandard
================

This project provides a Python C extension for interfacing with the
`Zstandard <http://www.zstd.net>`_ compression library.

The primary goal of the extension is to provide a Pythonic interface to
the underlying C API. This means exposing most of the features and flexibility
of the C API while not sacrificing usability or safety that Python provides.

|  |ci-status| |win-ci-status|

State of Project
================

The project is officially in alpha state. The main reason for this is
the author wishes to reserve the right to change the Python API. At the
time all desired functionality has been implemented and the project author
is satisfied with the Python API, the project will enter beta status.

There is continuous integration for Python versions 2.6, 2.7, and 3.3+
on Linux x86_x64 and Windows x86 and x86_64. The author is reasonably
confident the extension is stable and works as advertised on these
platforms.

Expected Changes
----------------

The author is reasonably confident in the current state of what's
implemented on the ``ZstdCompressor`` and ``ZstdDecompressor`` types.
Those APIs likely won't change significantly. Some low-level behavior
(such as naming and types expected by arguments) may change.

There will likely be arguments added to control the input and output
buffer sizes (currently, certain operations read and write in chunk
sizes using zstd's preferred defaults).

There should be an API that accepts an object that conforms to the buffer
interface and returns an iterator over compressed or decompressed output.

The author is on the fence as to whether to support the extremely
low level compression and decompression APIs. It could be useful to
support compression without the framing headers. But the author doesn't
believe it a high priority at this time.

The CFFI bindings are half-baked and need to be finished.

Requirements
============

This extension is designed to run with Python 2.6, 2.7, 3.3, 3.4, and 3.5
on common platforms (Linux, Windows, and OS X). Only x86_64 is currently
well-tested as an architecture.

Performance
===========

Very crude and non-scientific benchmarking (most benchmarks fall in this
category because proper benchmarking is hard) show that the Python bindings
perform within 10% of the native C implementation.

The following table compares the performance of compressing and decompressing
a 1.1 GB tar file comprised of the files in a Firefox source checkout. Values
obtained with the ``zstd`` program are on the left. The remaining columns detail
performance of various compression APIs in the Python bindings.

+-------+-----------------+-----------------+-----------------+---------------+
| Level | Native          | Simple          | Stream In       | Stream Out    |
|       | Comp / Decomp   | Comp / Decomp   | Comp / Decomp   | Comp          |
+=======+=================+=================+=================+===============+
|   1   | 490 / 1338 MB/s | 458 / 1266 MB/s | 407 / 1156 MB/s |  405 MB/s     |
+-------+-----------------+-----------------+-----------------+---------------+
|   2   | 412 / 1288 MB/s | 381 / 1203 MB/s | 345 / 1128 MB/s |  349 MB/s     |
+-------+-----------------+-----------------+-----------------+---------------+
|   3   | 342 / 1312 MB/s | 319 / 1182 MB/s | 285 / 1165 MB/s |  287 MB/s     |
+-------+-----------------+-----------------+-----------------+---------------+
|  11   |  64 / 1506 MB/s |  66 / 1436 MB/s |  56 / 1342 MB/s |   57 MB/s     |
+-------+-----------------+-----------------+-----------------+---------------+

Again, these are very unscientific. But it shows that Python is capable of
compressing at several hundred MB/s and decompressing at over 1 GB/s.

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

We recommend testing with ``nose``::

   $ nosetests

A Tox configuration is present to test against multiple Python versions::

   $ tox

Tests use the ``hypothesis`` Python package to perform fuzzing. If you
don't have it, those tests won't run.

There is also an experimental CFFI module. You need the ``cffi`` Python
package installed to build and test that.

To create a virtualenv with all development dependencies, do something
like the following::

  # Python 2
  $ virtualenv venv

  # Python 3
  $ python3 -m venv venv

  $ source venv/bin/activate
  $ pip install cffi hypothesis nose tox

API
===

The compiled C extension provides a ``zstd`` Python module. This module
exposes the following interfaces.

ZstdCompressor
--------------

The ``ZstdCompressor`` class provides an interface for performing
compression operations.

Each instance is associated with parameters that control compression
behavior. These come from the following named arguments (all optional):

level
   Integer compression level. Valid values are between 1 and 22.
dict_data
   Compression dictionary to use.

   Note: When using dictionary data and ``compress()`` is called multiple
   times, the ``CompressionParameters`` derived from an integer compression
   ``level`` and the first compressed data's size will be reused for all
   subsequent operations. This may not be desirable if source data size
   varies significantly.
compression_params
   A ``CompressionParameters`` instance (overrides the ``level`` value).
write_checksum
   Whether a 4 byte checksum should be written with the compressed data.
   Defaults to False. If True, the decompressor can verify that decompressed
   data matches the original input data.
write_content_size
   Whether the size of the uncompressed data will be written into the
   header of compressed data. Defaults to False. The data will only be
   written if the compressor knows the size of the input data. This is
   likely not true for streaming compression.
write_dict_id
   Whether to write the dictionary ID into the compressed data.
   Defaults to True. The dictionary ID is only written if a dictionary
   is being used.

Simple API
^^^^^^^^^^

``compress(data)`` compresses and returns data as a one-shot operation.::

   cctx = zstd.ZsdCompressor()
   compressed = cctx.compress(b'data to compress')

Streaming Input API
^^^^^^^^^^^^^^^^^^^

``write_to(fh)`` (which behaves as a context manager) allows you to *stream*
data into a compressor.::

   cctx = zstd.ZstdCompressor(level=10)
   with cctx.write_to(fh) as compressor:
       compressor.write(b'chunk 0')
	   compressor.write(b'chunk 1')
	   ...

The argument to ``write_to()`` must have a ``write(data)`` method. As
compressed data is available, ``write()`` will be called with the comrpessed
data as its argument. Many common Python types implement ``write()``, including
open file handles and ``io.BytesIO``.

``write_to()`` returns an object representing a streaming compressor instance.
It **must** be used as a context manager. That object's ``write(data)`` method
is used to feed data into the compressor.

If the size of the data being fed to this streaming compressor is known,
you can declare it before compression begins::

   cctx = zstd.ZstdCompressor()
   with cctx.write_to(fh, size=data_len) as compressor:
       compressor.write(chunk0)
	   compressor.write(chunk1)
	   ...

Declaring the size of the source data allows compression parameters to
be tuned. And if ``write_content_size`` is used, it also results in the
content size being written into the frame header of the output data.

To see how much memory is being used by the streaming compressor::

    cctx = zstd.ZstdCompressor()
	with cctx.write_to(fh) as compressor:
	    ...
		byte_size = compressor.memory_size()

Streaming Output API
^^^^^^^^^^^^^^^^^^^^

``read_from(reader)`` provides a mechanism to stream data out of a compressor
as an iterator of data chunks.::

   cctx = zstd.ZstdCompressor()
   for chunk in cctx.read_from(fh):
        # Do something with emitted data.

``read_from()`` will call ``.read(size)`` on the passed object to obtain
uncompressed data to feed into the compressor. The returned iterator consists
of chunks of compressed data.

Like ``write_to()``, ``read_from()`` also accepts a ``size`` argument
declaring the size of the input stream::

    cctx = zstd.ZstdCompressor()
	for chunk in cctx.read_from(fh, size=some_int):
	    pass

Stream Copying API
^^^^^^^^^^^^^^^^^^

``copy_stream(ifh, ofh)`` can be used to copy data between 2 streams while
compressing it.::

   cctx = zstd.ZstdCompressor()
   cctx.copy_stream(ifh, ofh)

For example, say you wish to compress a file::

   cctx = zstd.ZstdCompressor()
   with open(input_path, 'rb') as ifh, open(output_path, 'wb') as ofh:
	   cctx.copy_stream(ifh, ofh)

It is also possible to declare the size of the source stream::

   cctx = zstd.ZstdCompressor()
   cctx.copy_stream(ifh, ofh, size=len_of_input)

The stream copier returns a 2-tuple of bytes read and written::

   cctx = zstd.ZstdCompressor()
   read_count, write_count = cctx.copy_stream(ifh, ofh)

ZstdDecompressor
----------------

The ``ZstdDecompressor`` class provides an interface for performing
decompression.

Each instance is associated with parameters that control decompression. These
come from the following named arguments (all optional):

dict_data
   Compression dictionary to use.

The interface of this class is very similar to ``ZstdCompressor`` (by design).

Simple API
^^^^^^^^^^

``decompress(data)`` can be used to decompress an entire compressed zstd
frame in a single operation.::

    dctx = zstd.ZstdDecompressor()
	decompressed = dctx.decompress(data)

By default, ``decompress(data)`` will only work on data written with the content
size encoded in its header. This can be achieved by creating a
``ZstdCompressor`` with ``write_content_size=True``. If compressed data without
an embedded content size is seen, ``zstd.ZstdError`` will be raised.

If the compressed data doesn't have its content size embedded within it,
decompression can be attempted by specifying the ``max_output_size``
argument.::

    dctx = zstd.ZstdDecompressor()
	uncompressed = dctx.decompress(data, max_output_size=1048576)

Ideally, ``max_output_size`` will be identical to the decompressed output
size.

If ``max_output_size`` is too small to hold the decompressed data,
``zstd.ZstdError`` will be raised.

If ``max_output_size`` is larger than the decompressed data, the allocated
output buffer will be resized to only use the space required.

Please note that an allocation of the requested ``max_output_size`` will be
performed every time the method is called. Setting to a very large value could
result in a lot of work for the memory allocator and may result in
``MemoryError`` being raised if the allocation fails.

If the exact size of decompressed data is unknown, it is **strongly**
recommended to use a streaming API.

Streaming Input API
^^^^^^^^^^^^^^^^^^^

``write_to(fh)`` can be used to incrementally send compressed data to a
decompressor.::

    dctx = zstd.ZstdDecompressor()
    with dctx.write_to(fh) as decompressor:
        decompressor.write(compressed_data)

This behaves similarly to ``zstd.ZstdCompressor``: compressed data is written to
the decompressor by calling ``write(data)`` and decompressed output is written
to the output object by calling its ``write(data)`` method.

You can see how much memory is being used by the decompressor::

    dctx = zstd.ZstdDecompressor()
	with dctx.write_to(fh) as decompressor:
	    byte_size = decompressor.memory_size()

Streaming Output API
^^^^^^^^^^^^^^^^^^^^

``read_from(fh)`` provides a mechanism to stream decompressed data out of a
compressed source as an iterator of data chunks.:: 

    dctx = zstd.ZstdDecompressor()
	for chunk in dctx.read_from(fh):
	    # Do something with original data.

``read_from()`` accepts an object with a ``read(size)`` method that will
return compressed bytes. It returns an iterator whose elements are chunks
of the decompressed data.

Similarly to ``ZstdCompressor.read_from()``, the consumer of the iterator
controls when data is decompressed. If the iterator isn't consumed,
decompression is put on hold.

Stream Copying API
^^^^^^^^^^^^^^^^^^

``copy_stream(ifh, ofh)`` can be used to copy data across 2 streams while
performing decompression.::

    dctx = zstd.ZstdDecompressor()
    dctx.copy_stream(ifh, ofh)

e.g. to decompress a file to another file::

    dctx = zstd.ZstdDecompressor()
    with open(input_path, 'rb') as ifh, open(output_path, 'wb') as ofh:
        dctx.copy_stream(ifh, ofh)

Choosing an API
---------------

Various forms of compression and decompression APIs are provided because each
are suitable for different use cases.

The simple/one-shot APIs are useful for small data, when the decompressed
data size is known (either recorded in the zstd frame header via
``write_content_size`` or known via an out-of-band mechanism, such as a file
size).

A limitation of the simple APIs is that input or output data must fit in memory.
And unless using advanced tricks with Python *buffer objects*, both input and
output must fit in memory simultaneously.

Another limitation is that compression or decompression is performed as a single
operation. So if you feed large input, it could take a long time for the
function to return.

The streaming APIs do not have the limitations of the simple API. The cost to
this is they are more complex to use than a single function call.

The streaming APIs put the caller in control of compression and decompression
behavior by allowing them to directly control either the input or output side
of the operation.

With the streaming input APIs, the caller feeds data into the compressor or
decompressor as they see fit. Output data will only be written after the caller
has explicitly written data.

With the streaming output APIs, the caller consumes output from the compressor
or decompressor as they see fit. The compressor or decompressor will only
consume data from the source when the caller is ready to receive it.

One end of the streaming APIs involves a file-like object that must
``write()`` output data or ``read()`` input data. Depending on what the
backing storage for these objects is, those operations may not complete quickly.
For example, when streaming compressed data to a file, the ``write()`` into
a streaming compressor could result in a ``write()`` to the filesystem, which
may take a long time to finish due to slow I/O on the filesystem. So, there
may be overhead in streaming APIs beyond the compression and decompression
operations.

Dictionary Creation and Management
----------------------------------

Zstandard allows *dictionaries* to be used when compressing and
decompressing data. The idea is that if you are compressing a lot of similar
data, you can precompute common properties of that data (such as recurring
byte sequences) to achieve better compression ratios.

In Python, compression dictionaries are represented as the
``ZstdCompressionDict`` type.

Instances can be constructed from bytes::

   dict_data = zstd.ZstdCompressionDict(data)

More interestingly, instances can be created by *training* on sample data::

   dict_data = zstd.train_dictionary(size, samples)

This takes a list of bytes instances and creates and returns a
``ZstdCompressionDict``.

You can see how many bytes are in the dictionary by calling ``len()``::

   dict_data = zstd.train_dictionary(size, samples)
   dict_size = len(dict_data)  # will not be larger than ``size``

Once you have a dictionary, you can pass it to the objects performing
compression and decompression::

   dict_data = zstd.train_dictionary(16384, samples)

   cctx = zstd.ZstdCompressor(dict_data=data)
   for source_data in input_data:
       compressed = cctx.compress(source_data)
	   # Do something with compressed data.

   dctx = zstd.ZstdDecompressor(dict_data=dict_data)
   for compressed_data in input_data:
       buffer = io.BytesIO()
       with dctx.write_to(buffer) as decompressor:
	       decompressor.write(compressed_data)
	   # Do something with raw data in ``buffer``.

Dictionaries have unique integer IDs. You can retrieve this ID via::

   dict_id = zstd.dictionary_id(dict_data)

Explicit Compression Parameters
-------------------------------

Zstandard's integer compression levels along with the input size and dictionary
size are converted into a data structure defining multiple parameters to tune
behavior of the compression algorithm. It is possible to use define this
data structure explicitly to have lower-level control over compression behavior.

The ``zstd.CompressionParameters`` type represents this data structure.
You can see how Zstandard converts compression levels to this data structure
by calling ``zstd.get_compression_parameters()``. e.g.::

    params = zstd.get_compression_parameters(5)

This function also accepts the uncompressed data size and dictionary size
to adjust parameters::

    params = zstd.get_compression_parameters(3, source_size=len(data), dict_size=len(dict_data))

You can also construct compression parameters from their low-level components::

    params = zstd.CompressionParameters(20, 6, 12, 5, 4, 10, zstd.STRATEGY_FAST)

You can then configure a compressor to use the custom parameters::

    cctx = zstd.ZstdCompressor(compression_params=params)

The members of the ``CompressionParameters`` tuple are as follows::

* 0 - Window log
* 1 - Chain log
* 2 - Hash log
* 3 - Search log
* 4 - Search length
* 5 - Target length
* 6 - Strategy (one of the ``zstd.STRATEGY_`` constants)

You'll need to read the Zstandard documentation for what these parameters
do.

Misc Functionality
------------------

estimate_compression_context_size(CompressionParameters)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Given a ``CompressionParameters`` struct, estimate the memory size required
to perform compression.

estimate_decompression_context_size()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Estimate the memory size requirements for a decompressor instance.

Constants
---------

The following module constants/attributes are exposed:

ZSTD_VERSION
    This module attribute exposes a 3-tuple of the Zstandard version. e.g.
    ``(1, 0, 0)``
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

FRAME_HEADER
    bytes containing header of the Zstandard frame
MAGIC_NUMBER
    Frame header as an integer

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

Note on Zstandard's *Experimental* API
======================================

Many of the Zstandard APIs used by this module are marked as *experimental*
within the Zstandard project. This includes a large number of useful
features, such as compression and frame parameters and parts of dictionary
compression.

It is unclear how Zstandard's C API will evolve over time, especially with
regards to this *experimental* functionality. We will try to maintain
backwards compatibility at the Python API level. However, we cannot
guarantee this for things not under our control.

Since a copy of the Zstandard source code is distributed with this
module and since we compile against it, the behavior of a specific
version of this module should be constant for all of time. So if you
pin the version of this module used in your projects (which is a Python
best practice), you should be buffered from unwanted future changes.

.. |ci-status| image:: https://travis-ci.org/indygreg/python-zstandard.svg?branch=master
    :target: https://travis-ci.org/indygreg/python-zstandard

.. |win-ci-status| image:: https://ci.appveyor.com/api/projects/status/github/indygreg/python-zstandard?svg=true
    :target: https://ci.appveyor.com/project/indygreg/python-zstandard
    :alt: Windows build status
