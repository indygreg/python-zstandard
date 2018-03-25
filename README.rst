================
python-zstandard
================

This project provides Python bindings for interfacing with the
`Zstandard <http://www.zstd.net>`_ compression library. A C extension
and CFFI interface are provided.

The primary goal of the project is to provide a rich interface to the
underlying C API through a Pythonic interface while not sacrificing
performance. This means exposing most of the features and flexibility
of the C API while not sacrificing usability or safety that Python provides.

The canonical home for this project is
https://github.com/indygreg/python-zstandard.

|  |ci-status| |win-ci-status|

Requirements
============

This extension is designed to run with Python 2.7, 3.4, 3.5, and 3.6
on common platforms (Linux, Windows, and OS X). Only x86_64 is
currently well-tested as an architecture.

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

API
===

To interface with Zstandard, simply import the ``zstandard`` module::

   import zstandard

It is a popular convention to alias the module as a different name for
brevity::

   import zstandard as zstd

This module attempts to import and use either the C extension or CFFI
implementation. On Python platforms known to support C extensions (like
CPython), it raises an ImportError if the C extension cannot be imported.
On Python platforms known to not support C extensions (like PyPy), it only
attempts to import the CFFI implementation and raises ImportError if that
can't be done. On other platforms, it first tries to import the C extension
then falls back to CFFI if that fails and raises ImportError if CFFI fails.

To change the module import behavior, a ``PYTHON_ZSTANDARD_IMPORT_POLICY``
environment variable can be set. The following values are accepted:

default
   The behavior described above.
cffi_fallback
   Always try to import the C extension then fall back to CFFI if that
   fails.
cext
   Only attempt to import the C extension.
cffi
   Only attempt to import the CFFI implementation.

In addition, the ``zstandard`` module exports a ``backend`` attribute
containing the string name of the backend being used. It will be one
of ``cext`` or ``cffi`` (for *C extension* and *cffi*, respectively).

The types, functions, and attributes exposed by the ``zstandard`` module
are documented in the sections below.

.. note::

   The documentation in this section makes references to various zstd
   concepts and functionality. The ``Concepts`` section below explains
   these concepts in more detail.

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
   A ``CompressionParameters`` instance defining compression settings.
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
threads
   Enables and sets the number of threads to use for multi-threaded compression
   operations. Defaults to 0, which means to use single-threaded compression.
   Negative values will resolve to the number of logical CPUs in the system.
   Read below for more info on multi-threaded compression. This argument only
   controls thread count for operations that operate on individual pieces of
   data. APIs that spawn multiple threads for working on multiple pieces of
   data have their own ``threads`` argument.

``compression_params`` is mutually exclusive with ``level``, ``write_checksum``,
``write_content_size``, ``write_dict_id``, and ``threads``.

Unless specified otherwise, assume that no two methods of ``ZstdCompressor``
instances can be called from multiple Python threads simultaneously. In other
words, assume instances are not thread safe unless stated otherwise.

Utility Methods
^^^^^^^^^^^^^^^

``memory_size()`` obtains the memory utilization of the underlying zstd
compression context, in bytes.::

    cctx = zstd.ZstdCompressor()
    memory = cctx.memory_size()

Simple API
^^^^^^^^^^

``compress(data)`` compresses and returns data as a one-shot operation.::

   cctx = zstd.ZstdCompressor()
   compressed = cctx.compress(b'data to compress')

The ``data`` argument can be any object that implements the *buffer protocol*.

Unless ``compression_params`` or ``dict_data`` are passed to the
``ZstdCompressor``, each invocation of ``compress()`` will calculate the
optimal compression parameters for the configured compression ``level`` and
input data size (some parameters are fine-tuned for small input sizes).

If a compression dictionary is being used, the compression parameters
determined from the first input's size will be reused for subsequent
operations.

There is currently a deficiency in zstd's C APIs that makes it difficult
to round trip empty inputs when ``write_content_size=True``. Attempting
this will raise a ``ValueError`` unless ``allow_empty=True`` is passed
to ``compress()``.

Stream Reader API
^^^^^^^^^^^^^^^^^

``stream_reader(source)`` can be used to obtain an object conforming to the
``io.RawIOBase`` interface for reading compressed output as a stream::

   with open(path, 'rb') as fh:
       cctx = zstd.ZstdCompressor()
       with cctx.stream_reader(fh) as reader:
           while True:
               chunk = reader.read(16384)
               if not chunk:
                   break

               # Do something with compressed chunk.

The stream can only be read within a context manager. When the context
manager exits, the stream is closed and the underlying resource is
released and future operations against the stream will fail.

The ``source`` argument to ``stream_reader()`` can be any object with a
``read(size)`` method or any object implementing the *buffer protocol*.

``stream_reader()`` accepts a ``size`` argument specifying how large the input
stream is. This is used to adjust compression parameters so they are
tailored to the source size.::

   with open(path, 'rb') as fh:
       cctx = zstd.ZstdCompressor()
       with cctx.stream_reader(fh, size=os.stat(path).st_size) as reader:
           ...

If the ``source`` is a stream, you can specify how large ``read()`` requests
to that stream should be via the ``read_size`` argument. It defaults to
``zstandard.COMPRESSION_RECOMMENDED_INPUT_SIZE``.::

   with open(path, 'rb') as fh:
       cctx = zstd.ZstdCompressor()
       # Will perform fh.read(8192) when obtaining data for the compressor.
       with cctx.stream_reader(fh, read_size=8192) as reader:
           ...

The stream returned by ``stream_reader()`` is neither writable nor seekable
(even if the underlying source is seekable). ``readline()`` and
``readlines()`` are not implemented because they don't make sense for
compressed data. ``tell()`` returns the number of compressed bytes
emitted so far.

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
compressed data is available, ``write()`` will be called with the compressed
data as its argument. Many common Python types implement ``write()``, including
open file handles and ``io.BytesIO``.

``write_to()`` returns an object representing a streaming compressor instance.
It **must** be used as a context manager. That object's ``write(data)`` method
is used to feed data into the compressor.

A ``flush()`` method can be called to evict whatever data remains within the
compressor's internal state into the output object. This may result in 0 or
more ``write()`` calls to the output object.

Both ``write()`` and ``flush()`` return the number of bytes written to the
object's ``write()``. In many cases, small inputs do not accumulate enough
data to cause a write and ``write()`` will return ``0``.

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

The size of chunks being ``write()`` to the destination can be specified::

    cctx = zstd.ZstdCompressor()
    with cctx.write_to(fh, write_size=32768) as compressor:
        ...

To see how much memory is being used by the streaming compressor::

    cctx = zstd.ZstdCompressor()
    with cctx.write_to(fh) as compressor:
        ...
        byte_size = compressor.memory_size()

Streaming Output API
^^^^^^^^^^^^^^^^^^^^

``read_to_iter(reader)`` provides a mechanism to stream data out of a
compressor as an iterator of data chunks.::

   cctx = zstd.ZstdCompressor()
   for chunk in cctx.read_to_iter(fh):
        # Do something with emitted data.

``read_to_iter()`` accepts an object that has a ``read(size)`` method or
conforms to the buffer protocol.

Uncompressed data is fetched from the source either by calling ``read(size)``
or by fetching a slice of data from the object directly (in the case where
the buffer protocol is being used). The returned iterator consists of chunks
of compressed data.

If reading from the source via ``read()``, ``read()`` will be called until
it raises or returns an empty bytes (``b''``). It is perfectly valid for
the source to deliver fewer bytes than were what requested by ``read(size)``.

Like ``write_to()``, ``read_to_iter()`` also accepts a ``size`` argument
declaring the size of the input stream::

    cctx = zstd.ZstdCompressor()
    for chunk in cctx.read_to_iter(fh, size=some_int):
        pass

You can also control the size that data is ``read()`` from the source and
the ideal size of output chunks::

    cctx = zstd.ZstdCompressor()
    for chunk in cctx.read_to_iter(fh, read_size=16384, write_size=8192):
        pass

Unlike ``write_to()``, ``read_to_iter()`` does not give direct control
over the sizes of chunks fed into the compressor. Instead, chunk sizes will
be whatever the object being read from delivers. These will often be of a
uniform size.

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

You can also specify how large the chunks that are ``read()`` and ``write()``
from and to the streams::

   cctx = zstd.ZstdCompressor()
   cctx.copy_stream(ifh, ofh, read_size=32768, write_size=16384)

The stream copier returns a 2-tuple of bytes read and written::

   cctx = zstd.ZstdCompressor()
   read_count, write_count = cctx.copy_stream(ifh, ofh)

Compressor API
^^^^^^^^^^^^^^

``compressobj()`` returns an object that exposes ``compress(data)`` and
``flush()`` methods. Each returns compressed data or an empty bytes.

The purpose of ``compressobj()`` is to provide an API-compatible interface
with ``zlib.compressobj`` and ``bz2.BZ2Compressor``. This allows callers to
swap in different compressor objects while using the same API.

``flush()`` accepts an optional argument indicating how to end the stream.
``zstd.COMPRESSOBJ_FLUSH_FINISH`` (the default) ends the compression stream.
Once this type of flush is performed, ``compress()`` and ``flush()`` can
no longer be called. This type of flush **must** be called to end the
compression context. If not called, returned data may be incomplete.

A ``zstd.COMPRESSOBJ_FLUSH_BLOCK`` argument to ``flush()`` will flush a
zstd block. Flushes of this type can be performed multiple times. The next
call to ``compress()`` will begin a new zstd block.

Here is how this API should be used::

   cctx = zstd.ZstdCompressor()
   cobj = cctx.compressobj()
   data = cobj.compress(b'raw input 0')
   data = cobj.compress(b'raw input 1')
   data = cobj.flush()

Or to flush blocks::

   cctx.zstd.ZstdCompressor()
   cobj = cctx.compressobj()
   data = cobj.compress(b'chunk in first block')
   data = cobj.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK)
   data = cobj.compress(b'chunk in second block')
   data = cobj.flush()

For best performance results, keep input chunks under 256KB. This avoids
extra allocations for a large output object.

It is possible to declare the input size of the data that will be fed into
the compressor::

   cctx = zstd.ZstdCompressor()
   cobj = cctx.compressobj(size=6)
   data = cobj.compress(b'foobar')
   data = cobj.flush()

Batch Compression API
^^^^^^^^^^^^^^^^^^^^^

(Experimental. Not yet supported in CFFI bindings.)

``multi_compress_to_buffer(data, [threads=0])`` performs compression of multiple
inputs as a single operation.

Data to be compressed can be passed as a ``BufferWithSegmentsCollection``, a
``BufferWithSegments``, or a list containing byte like objects. Each element of
the container will be compressed individually using the configured parameters
on the ``ZstdCompressor`` instance.

The ``threads`` argument controls how many threads to use for compression. The
default is ``0`` which means to use a single thread. Negative values use the
number of logical CPUs in the machine.

The function returns a ``BufferWithSegmentsCollection``. This type represents
N discrete memory allocations, eaching holding 1 or more compressed frames.

Output data is written to shared memory buffers. This means that unlike
regular Python objects, a reference to *any* object within the collection
keeps the shared buffer and therefore memory backing it alive. This can have
undesirable effects on process memory usage.

The API and behavior of this function is experimental and will likely change.
Known deficiencies include:

* If asked to use multiple threads, it will always spawn that many threads,
  even if the input is too small to use them. It should automatically lower
  the thread count when the extra threads would just add overhead.
* The buffer allocation strategy is fixed. There is room to make it dynamic,
  perhaps even to allow one output buffer per input, facilitating a variation
  of the API to return a list without the adverse effects of shared memory
  buffers.

ZstdDecompressor
----------------

The ``ZstdDecompressor`` class provides an interface for performing
decompression.

Each instance is associated with parameters that control decompression. These
come from the following named arguments (all optional):

dict_data
   Compression dictionary to use.

The interface of this class is very similar to ``ZstdCompressor`` (by design).

Unless specified otherwise, assume that no two methods of ``ZstdDecompressor``
instances can be called from multiple Python threads simultaneously. In other
words, assume instances are not thread safe unless stated otherwise.

Utility Methods
^^^^^^^^^^^^^^^

``memory_size()`` obtains the size of the underlying zstd decompression context,
in bytes.::

    dctx = zstd.ZstdDecompressor()
    size = dctx.memory_size()

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

Stream Reader API
^^^^^^^^^^^^^^^^^

``stream_reader(source)`` can be used to obtain an object conforming to the
``io.RawIOBase`` interface for reading decompressed output as a stream::

   with open(path, 'rb') as fh:
       dctx = zstd.ZstdDecompressor()
       with dctx.stream_reader(fh) as reader:
           while True:
               chunk = reader.read(16384)
               if not chunk:
                   break

               # Do something with decompressed chunk.

The stream can only be read within a context manager. When the context
manager exits, the stream is closed and the underlying resource is
released and future operations against the stream will fail.

The ``source`` argument to ``stream_reader()`` can be any object with a
``read(size)`` method or any object implementing the *buffer protocol*.

If the ``source`` is a stream, you can specify how large ``read()`` requests
to that stream should be via the ``read_size`` argument. It defaults to
``zstandard.DECOMPRESSION_RECOMMENDED_INPUT_SIZE``.::

   with open(path, 'rb') as fh:
       dctx = zstd.ZstdDecompressor()
       # Will perform fh.read(8192) when obtaining data for the decompressor.
       with dctx.stream_reader(fh, read_size=8192) as reader:
           ...

The stream returned by ``stream_reader()`` is neither writable nor seekable
``tell()`` returns the number of decompressed bytes emitted so far.

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

Calls to ``write()`` will return the number of bytes written to the output
object. Not all inputs will result in bytes being written, so return values
of ``0`` are possible.

The size of chunks being ``write()`` to the destination can be specified::

    dctx = zstd.ZstdDecompressor()
    with dctx.write_to(fh, write_size=16384) as decompressor:
        pass

You can see how much memory is being used by the decompressor::

    dctx = zstd.ZstdDecompressor()
    with dctx.write_to(fh) as decompressor:
        byte_size = decompressor.memory_size()

Streaming Output API
^^^^^^^^^^^^^^^^^^^^

``read_to_iter(fh)`` provides a mechanism to stream decompressed data out of a
compressed source as an iterator of data chunks.:: 

    dctx = zstd.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh):
        # Do something with original data.

``read_to_iter()`` accepts a) an object with a ``read(size)`` method that will
return  compressed bytes b) an object conforming to the buffer protocol that
can expose its data as a contiguous range of bytes.

``read_to_iter()`` returns an iterator whose elements are chunks of the
decompressed data.

The size of requested ``read()`` from the source can be specified::

    dctx = zstd.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh, read_size=16384):
        pass

It is also possible to skip leading bytes in the input data::

    dctx = zstd.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh, skip_bytes=1):
        pass

Skipping leading bytes is useful if the source data contains extra
*header* data but you want to avoid the overhead of making a buffer copy
or allocating a new ``memoryview`` object in order to decompress the data.

Similarly to ``ZstdCompressor.read_to_iter()``, the consumer of the iterator
controls when data is decompressed. If the iterator isn't consumed,
decompression is put on hold.

When ``read_to_iter()`` is passed an object conforming to the buffer protocol,
the behavior may seem similar to what occurs when the simple decompression
API is used. However, this API works when the decompressed size is unknown.
Furthermore, if feeding large inputs, the decompressor will work in chunks
instead of performing a single operation.

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

The size of chunks being ``read()`` and ``write()`` from and to the streams
can be specified::

    dctx = zstd.ZstdDecompressor()
    dctx.copy_stream(ifh, ofh, read_size=8192, write_size=16384)

Decompressor API
^^^^^^^^^^^^^^^^

``decompressobj()`` returns an object that exposes a ``decompress(data)``
method. Compressed data chunks are fed into ``decompress(data)`` and
uncompressed output (or an empty bytes) is returned. Output from subsequent
calls needs to be concatenated to reassemble the full decompressed byte
sequence.

The purpose of ``decompressobj()`` is to provide an API-compatible interface
with ``zlib.decompressobj`` and ``bz2.BZ2Decompressor``. This allows callers
to swap in different decompressor objects while using the same API.

Each object is single use: once an input frame is decoded, ``decompress()``
can no longer be called.

Here is how this API should be used::

   dctx = zstd.ZstdDecompressor()
   dobj = dctx.decompressobj()
   data = dobj.decompress(compressed_chunk_0)
   data = dobj.decompress(compressed_chunk_1)

By default, calls to ``decompress()`` write output data in chunks of size
``DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE``. These chunks are concatenated
before being returned to the caller. It is possible to define the size of
these temporary chunks by passing ``write_size`` to ``decompressobj()``::

   dctx = zstd.ZstdDecompressor()
   dobj = dctx.decompressobj(write_size=1048576)

.. note::

   Because calls to ``decompress()`` may need to perform multiple
   memory (re)allocations, this streaming decompression API isn't as
   efficient as other APIs.

Batch Decompression API
^^^^^^^^^^^^^^^^^^^^^^^

(Experimental. Not yet supported in CFFI bindings.)

``multi_decompress_to_buffer()`` performs decompression of multiple
frames as a single operation and returns a ``BufferWithSegmentsCollection``
containing decompressed data for all inputs.

Compressed frames can be passed to the function as a ``BufferWithSegments``,
a ``BufferWithSegmentsCollection``, or as a list containing objects that
conform to the buffer protocol. For best performance, pass a
``BufferWithSegmentsCollection`` or a ``BufferWithSegments``, as
minimal input validation will be done for that type. If calling from
Python (as opposed to C), constructing one of these instances may add
overhead cancelling out the performance overhead of validation for list
inputs.

The decompressed size of each frame must be discoverable. It can either be
embedded within the zstd frame (``write_content_size=True`` argument to
``ZstdCompressor``) or passed in via the ``decompressed_sizes`` argument.

The ``decompressed_sizes`` argument is an object conforming to the buffer
protocol which holds an array of 64-bit unsigned integers in the machine's
native format defining the decompressed sizes of each frame. If this argument
is passed, it avoids having to scan each frame for its decompressed size.
This frame scanning can add noticeable overhead in some scenarios.

The ``threads`` argument controls the number of threads to use to perform
decompression operations. The default (``0``) or the value ``1`` means to
use a single thread. Negative values use the number of logical CPUs in the
machine.

.. note::

   It is possible to pass a ``mmap.mmap()`` instance into this function by
   wrapping it with a ``BufferWithSegments`` instance (which will define the
   offsets of frames within the memory mapped region).

This function is logically equivalent to performing ``dctx.decompress()``
on each input frame and returning the result.

This function exists to perform decompression on multiple frames as fast
as possible by having as little overhead as possible. Since decompression is
performed as a single operation and since the decompressed output is stored in
a single buffer, extra memory allocations, Python objects, and Python function
calls are avoided. This is ideal for scenarios where callers need to access
decompressed data for multiple frames.

Currently, the implementation always spawns multiple threads when requested,
even if the amount of work to do is small. In the future, it will be smarter
about avoiding threads and their associated overhead when the amount of
work to do is small.

Content-Only Dictionary Chain Decompression
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``decompress_content_dict_chain(frames)`` performs decompression of a list of
zstd frames produced using chained *content-only* dictionary compression. Such
a list of frames is produced by compressing discrete inputs where each
non-initial input is compressed with a *content-only* dictionary consisting
of the content of the previous input.

For example, say you have the following inputs::

   inputs = [b'input 1', b'input 2', b'input 3']

The zstd frame chain consists of:

1. ``b'input 1'`` compressed in standalone/discrete mode
2. ``b'input 2'`` compressed using ``b'input 1'`` as a *content-only* dictionary
3. ``b'input 3'`` compressed using ``b'input 2'`` as a *content-only* dictionary

Each zstd frame **must** have the content size written.

The following Python code can be used to produce a *content-only dictionary
chain*::

    def make_chain(inputs):
        frames = []

        # First frame is compressed in standalone/discrete mode.
        zctx = zstd.ZstdCompressor(write_content_size=True)
        frames.append(zctx.compress(inputs[0]))

        # Subsequent frames use the previous fulltext as a content-only dictionary
        for i, raw in enumerate(inputs[1:]):
            dict_data = zstd.ZstdCompressionDict(inputs[i])
            zctx = zstd.ZstdCompressor(write_content_size=True, dict_data=dict_data)
            frames.append(zctx.compress(raw))

        return frames

``decompress_content_dict_chain()`` returns the uncompressed data of the last
element in the input chain.

It is possible to implement *content-only dictionary chain* decompression
on top of other Python APIs. However, this function will likely be significantly
faster, especially for long input chains, as it avoids the overhead of
instantiating and passing around intermediate objects between C and Python.

Multi-Threaded Compression
--------------------------

``ZstdCompressor`` accepts a ``threads`` argument that controls the number
of threads to use for compression. The way this works is that input is split
into segments and each segment is fed into a worker pool for compression. Once
a segment is compressed, it is flushed/appended to the output.

The segment size for multi-threaded compression is chosen from the window size
of the compressor. This is derived from the ``window_log`` attribute of a
``CompressionParameters`` instance. By default, segment sizes are in the 1+MB
range.

If multi-threaded compression is requested and the input is smaller than the
configured segment size, only a single compression thread will be used. If the
input is smaller than the segment size multiplied by the thread pool size or
if data cannot be delivered to the compressor fast enough, not all requested
compressor threads may be active simultaneously.

Compared to non-multi-threaded compression, multi-threaded compression has
higher per-operation overhead. This includes extra memory operations,
thread creation, lock acquisition, etc.

Due to the nature of multi-threaded compression using *N* compression
*states*, the output from multi-threaded compression will likely be larger
than non-multi-threaded compression. The difference is usually small. But
there is a CPU/wall time versus size trade off that may warrant investigation.

Output from multi-threaded compression does not require any special handling
on the decompression side. In other words, any zstd decompressor should be able
to consume data produced with multi-threaded compression.

Dictionary Creation and Management
----------------------------------

Compression dictionaries are represented as the ``ZstdCompressionDict`` type.

Instances can be constructed from bytes::

   dict_data = zstd.ZstdCompressionDict(data)

It is possible to construct a dictionary from *any* data. If the data doesn't
begin with a magic header, it will be treated as a *content-only* dictionary.
*Content-only* dictionaries allow compression operations to reference raw data
within the dictionary.

It is possible to force the use of *content-only* dictionaries or to
require a dictionary header:

   dict_data = zstd.ZstdCompressionDict(data,
                                        dict_mode=zstd.DICT_MODE_RAWCONTENT)

   dict_data = zstd.ZstdCompressionDict(data,
                                        dict_mode=zstd.DICT_MODE_FULLDICT)

More interestingly, instances can be created by *training* on sample data::

   dict_data = zstd.train_dictionary(size, samples)

This takes a target dictionary size and list of bytes instances and creates and
returns a ``ZstdCompressionDict``.

You can see how many bytes are in the dictionary by calling ``len()``::

   dict_data = zstd.train_dictionary(size, samples)
   dict_size = len(dict_data)  # will not be larger than ``size``

Once you have a dictionary, you can pass it to the objects performing
compression and decompression::

   dict_data = zstd.train_dictionary(16384, samples)

   cctx = zstd.ZstdCompressor(dict_data=dict_data)
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

You can obtain the raw data in the dict (useful for persisting and constructing
a ``ZstdCompressionDict`` later) via ``as_bytes()``::

   dict_data = zstd.train_dictionary(size, samples)
   raw_data = dict_data.as_bytes()

By default, when a ``ZstdCompressionDict`` is *attached* to a
``ZstdCompressor``, each ``ZstdCompressor`` performs work to prepare the
dictionary for use. This is fine if only 1 compression operation is being
performed or if the ``ZstdCompressor`` is being reused for multiple operations.
But if multiple ``ZstdCompressor`` instances are being used with the dictionary,
this can add overhead.

It is possible to *precompute* the dictionary so it can readily be consumed
by multiple ``ZstdCompressor`` instances::

    d = zstd.ZstdCompressionDict(data)

    # Precompute for compression level 3.
    d.precompute_compress(level=3)

    # Precompute with specific compression parameters.
    params = zstd.CompressionParameters(...)
    d.precompute_compress(compression_params=params)

.. note::

   When a dictionary is precomputed, the compression parameters used to
   precompute the dictionary overwrite some of the compression parameters
   specified to ``ZstdCompressor.__init__``.

The dictionary training mechanism is known as *cover*. More details about it are
available in the paper *Effective Construction of Relative Lempel-Ziv
Dictionaries* (authors: Liao, Petri, Moffat, Wirth).

The cover algorithm takes parameters ``k` and ``d``. These are the
*segment size* and *dmer size*, respectively. The returned dictionary
instance created by this function has ``k`` and ``d`` attributes
containing the values for these parameters. If a ``ZstdCompressionDict``
is constructed from raw bytes data (a content-only dictionary), the
``k`` and ``d`` attributes will be ``0``.

The segment and dmer size parameters to the cover algorithm can either be
specified manually or ``train_dictionary()`` can try multiple values
and pick the best one, where *best* means the smallest compressed data size.
This later mode is called *optimization* mode.

If none of ``k``, ``d``, ``steps``, ``threads``, ``level``, ``notifications``,
or ``dict_id`` (basically anything from the underlying ``ZDICT_cover_params_t``
struct) are defined, *optimization* mode is used with default parameter
values.

If ``steps`` or ``threads`` are defined, then *optimization* mode is engaged
with explicit control over those parameters. Specifying ``threads=0`` or
``threads=1`` can be used to engage *optimization* mode if other parameters
are not defined.

Otherwise, non-*optimization* mode is used with the parameters specified.

This function takes the following arguments:

dict_size
   Target size in bytes of the dictionary to generate.
samples
   A list of bytes holding samples the dictionary will be trained from.
k
   Parameter to cover algorithm defining the segment size. A reasonable range
   is [16, 2048+].
d
   Parameter to cover algorithm defining the dmer size. A reasonable range is
   [6, 16]. ``d`` must be less than or equal to ``k``.
dict_id
   Integer dictionary ID for the produced dictionary. Default is 0, which uses
   a random value.
steps
   Number of steps through ``k`` values to perform when trying parameter
   variations.
threads
   Number of threads to use when trying parameter variations. Default is 0,
   which means to use a single thread. A negative value can be specified to
   use as many threads as there are detected logical CPUs.
level
   Integer target compression level when trying parameter variations.
notifications
   Controls writing of informational messages to ``stderr``. ``0`` (the
   default) means to write nothing. ``1`` writes errors. ``2`` writes
   progression info. ``3`` writes more details. And ``4`` writes all info.

Explicit Compression Parameters
-------------------------------

Zstandard offers a high-level *compression level* that maps to lower-level
compression parameters. For many consumers, this numeric level is the only
compression setting you'll need to touch.

But for advanced use cases, it might be desirable to tweak these lower-level
settings.

The ``CompressionParameters`` type represents these low-level compression
settings.

Instances of this type can be constructed from a myriad of keyword arguments
(defined below) for complete low-level control over each adjustable
compression setting.

From a higher level, one can construct a ``CompressionParameters`` instance
given a desired compression level and target input and dictionary size
using ``CompressionParameters.from_level()``. e.g.::

    # Derive compression settings for compression level 7.
    params = zstd.CompressionParameters.from_level(7)

    # With an input size of 1MB
    params = zstd.CompressionParameters.from_level(7, source_size=1048576)

Using ``from_level()``, it is also possible to override individual compression
parameters or to define additional settings that aren't automatically derived.
e.g.::

    params = zstd.CompressionParameters.from_level(4, window_log=10)
    params = zstd.CompressionParameters.from_level(5, threads=4)

Or you can define low-level compression settings directly::

    params = zstd.CompressionParameters(window_log=12, enable_ldm=True)

Once a ``CompressionParameters`` instance is obtained, it can be used to
configure a compressor::

    cctx = zstd.ZstdCompressor(compression_params=params)

The named arguments and attributes of ``CompressionParameters`` are as follows:

* format
* compression_level
* window_log
* hash_log
* chain_log
* search_log
* min_match
* target_length
* compression_strategy
* write_content_size
* write_checksum
* write_dict_id
* job_size
* overlap_size_log
* force_max_window
* enable_ldm
* ldm_hash_log
* ldm_min_match
* ldm_bucket_size_log
* ldm_hash_every_log
* threads

Some of these are very low-level settings. It may help to consult the official
zstandard documentation for their behavior. Look for the ``ZSTD_p_*`` constants
in ``zstd.h`` (https://github.com/facebook/zstd/blob/dev/lib/zstd.h).

Frame Inspection
----------------

Data emitted from zstd compression is encapsulated in a *frame*. This frame
begins with a 4 byte *magic number* header followed by 2 to 14 bytes describing
the frame in more detail. For more info, see
https://github.com/facebook/zstd/blob/master/doc/zstd_compression_format.md.

``zstd.get_frame_parameters(data)`` parses a zstd *frame* header from a bytes
instance and return a ``FrameParameters`` object describing the frame.

Depending on which fields are present in the frame and their values, the
length of the frame parameters varies. If insufficient bytes are passed
in to fully parse the frame parameters, ``ZstdError`` is raised. To ensure
frame parameters can be parsed, pass in at least 18 bytes.

``FrameParameters`` instances have the following attributes:

content_size
   Integer size of original, uncompressed content. This will be ``0`` if the
   original content size isn't written to the frame (controlled with the
   ``write_content_size`` argument to ``ZstdCompressor``) or if the input
   content size was ``0``.

window_size
   Integer size of maximum back-reference distance in compressed data.

dict_id
   Integer of dictionary ID used for compression. ``0`` if no dictionary
   ID was used or if the dictionary ID was ``0``.

has_checksum
   Bool indicating whether a 4 byte content checksum is stored at the end
   of the frame.

Misc Functionality
------------------

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

CONTENTSIZE_UNKNOWN
    Value for content size when the content size is unknown.
CONTENTSIZE_ERROR
    Value for content size when content size couldn't be determined.

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
    Compression strategy
STRATEGY_DFAST
    Compression strategy
STRATEGY_GREEDY
    Compression strategy
STRATEGY_LAZY
    Compression strategy
STRATEGY_LAZY2
    Compression strategy
STRATEGY_BTLAZY2
    Compression strategy
STRATEGY_BTOPT
    Compression strategy
STRATEGY_BTULTRA
    Compression strategy

Performance Considerations
--------------------------

The ``ZstdCompressor`` and ``ZstdDecompressor`` types maintain state to a
persistent compression or decompression *context*. Reusing a ``ZstdCompressor``
or ``ZstdDecompressor`` instance for multiple operations is faster than
instantiating a new ``ZstdCompressor`` or ``ZstdDecompressor`` for each
operation. The differences are magnified as the size of data decreases. For
example, the difference between *context* reuse and non-reuse for 100,000
100 byte inputs will be significant (possiby over 10x faster to reuse contexts)
whereas 10 1,000,000 byte inputs will be more similar in speed (because the
time spent doing compression dwarfs time spent creating new *contexts*).

Buffer Types
------------

The API exposes a handful of custom types for interfacing with memory buffers.
The primary goal of these types is to facilitate efficient multi-object
operations.

The essential idea is to have a single memory allocation provide backing
storage for multiple logical objects. This has 2 main advantages: fewer
allocations and optimal memory access patterns. This avoids having to allocate
a Python object for each logical object and furthermore ensures that access of
data for objects can be sequential (read: fast) in memory.

BufferWithSegments
^^^^^^^^^^^^^^^^^^

The ``BufferWithSegments`` type represents a memory buffer containing N
discrete items of known lengths (segments). It is essentially a fixed size
memory address and an array of 2-tuples of ``(offset, length)`` 64-bit
unsigned native endian integers defining the byte offset and length of each
segment within the buffer.

Instances behave like containers.

``len()`` returns the number of segments within the instance.

``o[index]`` or ``__getitem__`` obtains a ``BufferSegment`` representing an
individual segment within the backing buffer. That returned object references
(not copies) memory. This means that iterating all objects doesn't copy
data within the buffer.

The ``.size`` attribute contains the total size in bytes of the backing
buffer.

Instances conform to the buffer protocol. So a reference to the backing bytes
can be obtained via ``memoryview(o)``. A *copy* of the backing bytes can also
be obtained via ``.tobytes()``.

The ``.segments`` attribute exposes the array of ``(offset, length)`` for
segments within the buffer. It is a ``BufferSegments`` type.

BufferSegment
^^^^^^^^^^^^^

The ``BufferSegment`` type represents a segment within a ``BufferWithSegments``.
It is essentially a reference to N bytes within a ``BufferWithSegments``.

``len()`` returns the length of the segment in bytes.

``.offset`` contains the byte offset of this segment within its parent
``BufferWithSegments`` instance.

The object conforms to the buffer protocol. ``.tobytes()`` can be called to
obtain a ``bytes`` instance with a copy of the backing bytes.

BufferSegments
^^^^^^^^^^^^^^

This type represents an array of ``(offset, length)`` integers defining segments
within a ``BufferWithSegments``.

The array members are 64-bit unsigned integers using host/native bit order.

Instances conform to the buffer protocol.

BufferWithSegmentsCollection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``BufferWithSegmentsCollection`` type represents a virtual spanning view
of multiple ``BufferWithSegments`` instances.

Instances are constructed from 1 or more ``BufferWithSegments`` instances. The
resulting object behaves like an ordered sequence whose members are the
segments within each ``BufferWithSegments``.

``len()`` returns the number of segments within all ``BufferWithSegments``
instances.

``o[index]`` and ``__getitem__(index)`` return the ``BufferSegment`` at
that offset as if all ``BufferWithSegments`` instances were a single
entity.

If the object is composed of 2 ``BufferWithSegments`` instances with the
first having 2 segments and the second have 3 segments, then ``b[0]``
and ``b[1]`` access segments in the first object and ``b[2]``, ``b[3]``,
and ``b[4]`` access segments from the second.

Choosing an API
===============

There are multiple APIs for performing compression and decompression. This is
because different applications have different needs and the library wants to
facilitate optimal use in as many use cases as possible.

From a high-level, APIs are divided into *one-shot* and *streaming*. See
the ``Concepts`` section for a description of how these are different at
the C layer.

The *one-shot* APIs are useful for small data, where the input or output
size is known. (The size can come from a buffer length, file size, or
stored in the zstd frame header.) A limitation of the *one-shot* APIs is that
input and output must fit in memory simultaneously. For say a 4 GB input,
this is often not feasible.

The *one-shot* APIs also perform all work as a single operation. So, if you
feed it large input, it could take a long time for the function to return.

The streaming APIs do not have the limitations of the simple API. But the
price you pay for this flexibility is that they are more complex than a
single function call.

The streaming APIs put the caller in control of compression and decompression
behavior by allowing them to directly control either the input or output side
of the operation.

With the *streaming input*, *compressor*, and *decompressor* APIs, the caller
has full control over the input to the compression or decompression stream.
They can directly choose when new data is operated on.

With the *streaming ouput* APIs, the caller has full control over the output
of the compression or decompression stream. It can choose when to receive
new data.

When using the *streaming* APIs that operate on file-like or stream objects,
it is important to consider what happens in that object when I/O is requested.
There is potential for long pauses as data is read or written from the
underlying stream (say from interacting with a filesystem or network). This
could add considerable overhead.

Thread Safety
=============

``ZstdCompressor`` and ``ZstdDecompressor`` instances have no guarantees
about thread safety. Do not operate on the same ``ZstdCompressor`` and
``ZstdDecompressor`` instance simultaneously from different threads. It is
fine to have different threads call into a single instance, just not at the
same time.

Some operations require multiple function calls to complete. e.g. streaming
operations. A single ``ZstdCompressor`` or ``ZstdDecompressor`` cannot be used
for simultaneously active operations. e.g. you must not start a streaming
operation when another streaming operation is already active.

The C extension releases the GIL during non-trivial calls into the zstd C
API. Non-trivial calls are notably compression and decompression. Trivial
calls are things like parsing frame parameters. Where the GIL is released
is considered an implementation detail and can change in any release.

APIs that accept bytes-like objects don't enforce that the underlying object
is read-only. However, it is assumed that the passed object is read-only for
the duration of the function call. It is possible to pass a mutable object
(like a ``bytearray``) to e.g. ``ZstdCompressor.compress()``, have the GIL
released, and mutate the object from another thread. Such a race condition
is a bug in the consumer of python-zstandard. Most Python data types are
immutable, so unless you are doing something fancy, you don't need to
worry about this.

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

Donate
======

A lot of time has been invested into this project by the author.

If you find this project useful and would like to thank the author for
their work, consider donating some money. Any amount is appreciated.

.. image:: https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif
    :target: https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=gregory%2eszorc%40gmail%2ecom&lc=US&item_name=python%2dzstandard&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donate_LG%2egif%3aNonHosted
    :alt: Donate via PayPal

.. |ci-status| image:: https://travis-ci.org/indygreg/python-zstandard.svg?branch=master
    :target: https://travis-ci.org/indygreg/python-zstandard

.. |win-ci-status| image:: https://ci.appveyor.com/api/projects/status/github/indygreg/python-zstandard?svg=true
    :target: https://ci.appveyor.com/project/indygreg/python-zstandard
    :alt: Windows build status
