.. _compressor:

=======================
``ZstdCompressor`` Type
=======================

The ``zstandard.ZstdCompressor`` type provides an interface for performing
compression operations. Each instance is essentially a wrapper around a
``ZSTD_CCtx`` from the C API.

Instantiating
=============

Each ``ZstdCompressor`` instance is associated with parameters that
control compression behavior. These parameters are defined via the
following named arguments (all optional):

``level``
   Integer compression level. Valid values are between 1 and 22.
``dict_data``
   Compression dictionary to use.

   Note: When using dictionary data and ``compress()`` is called multiple
   times, the ``ZstdCompressionParameters`` derived from an integer
   compression ``level`` and the first compressed data's size will be reused
   for all subsequent operations. This may not be desirable if source data
   size varies significantly.
``compression_params``
   A ``ZstdCompressionParameters`` instance defining compression settings.
``write_checksum``
   Whether a 4 byte checksum should be written with the compressed data.
   Defaults to False. If True, the decompressor can verify that decompressed
   data matches the original input data.
``write_content_size``
   Whether the size of the uncompressed data will be written into the
   header of compressed data. Defaults to True. The data will only be
   written if the compressor knows the size of the input data. This is
   often not true for streaming compression.
``write_dict_id``
   Whether to write the dictionary ID into the compressed data.
   Defaults to True. The dictionary ID is only written if a dictionary
   is being used.
``threads``
   Enables and sets the number of threads to use for multi-threaded compression
   operations. Defaults to ``0``, which means to use single-threaded compression.
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
===============

``frame_progression()``
-----------------------

Returns a 3-tuple containing the number of bytes ingested, consumed, and
produced by the current compression operation.

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   (ingested, consumed, produced) = cctx.frame_progression()

``memory_size()``
-----------------

Obtains the memory utilization of the underlying zstd compression context, in
bytes.

.. code-block:: python

    cctx = zstandard.ZstdCompressor()
    memory = cctx.memory_size()

One-Shot Compression
====================

``compress(data)`` compresses and returns data as a one-shot operation.

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   compressed = cctx.compress(b'data to compress')

The ``data`` argument can be any object that implements the *buffer protocol*.

Stream Reader Interface
=======================

``stream_reader(source)`` can be used to obtain an object conforming to the
``io.RawIOBase`` interface for reading compressed output as a stream.

.. code-block:: python

   with open(path, 'rb') as fh:
       cctx = zstandard.ZstdCompressor()
       reader = cctx.stream_reader(fh)
       while True:
           chunk = reader.read(16384)
           if not chunk:
               break

           # Do something with compressed chunk.

Instances can also be used as context managers:

.. code-block:: python

   with open(path, 'rb') as fh:
       with cctx.stream_reader(fh) as reader:
           while True:
               chunk = reader.read(16384)
               if not chunk:
                   break

               # Do something with compressed chunk.

When the context manager exits or ``close()`` is called, the stream is closed,
underlying resources are released, and future operations against the compression
stream will fail.

The ``source`` argument to ``stream_reader()`` can be any object with a
``read(size)`` method or any object implementing the *buffer protocol*.

``stream_reader()`` accepts a ``size`` argument specifying how large the input
stream is. This is used to adjust compression parameters so they are
tailored to the source size.::

   with open(path, 'rb') as fh:
       cctx = zstandard.ZstdCompressor()
       with cctx.stream_reader(fh, size=os.stat(path).st_size) as reader:
           ...

If the ``source`` is a stream, you can specify how large ``read()`` requests
to that stream should be via the ``read_size`` argument. It defaults to
``zstandard.COMPRESSION_RECOMMENDED_INPUT_SIZE``.::

   with open(path, 'rb') as fh:
       cctx = zstandard.ZstdCompressor()
       # Will perform fh.read(8192) when obtaining data to feed into the
       # compressor.
       with cctx.stream_reader(fh, read_size=8192) as reader:
           ...

The stream returned by ``stream_reader()`` is neither writable nor seekable
(even if the underlying source is seekable). ``readline()`` and
``readlines()`` are not implemented because they don't make sense for
compressed data. ``tell()`` returns the number of compressed bytes
emitted so far.

The ``closefd`` keyword argument defines whether to close the underlying stream
when this instance is itself ``close()``d. The default is ``False``.

Stream Writer Interface
=======================

``stream_writer(fh)`` allows you to *stream* data into a compressor.

Returned instances implement the ``io.RawIOBase`` interface. Only methods
that involve writing will do useful things.

The argument to ``stream_writer()`` must have a ``write(data)`` method. As
compressed data is available, ``write()`` will be called with the compressed
data as its argument. Many common Python types implement ``write()``, including
open file handles and ``io.BytesIO``.

The ``write(data)`` method is used to feed data into the compressor.

The ``flush([flush_mode=FLUSH_BLOCK])`` method can be called to evict whatever
data remains within the compressor's internal state into the output object. This
may result in 0 or more ``write()`` calls to the output object. This method
accepts an optional ``flush_mode`` argument to control the flushing behavior.
Its value can be any of the ``FLUSH_*`` constants.

Both ``write()`` and ``flush()`` return the number of bytes written to the
object's ``write()``. In many cases, small inputs do not accumulate enough
data to cause a write and ``write()`` will return ``0``.

Calling ``close()`` will mark the stream as closed and subsequent I/O
operations will raise ``ValueError`` (per the documented behavior of
``io.RawIOBase``). ``close()`` will also call ``close()`` on the underlying
stream if such a method exists.

Typically usage is as follows:

.. code-block:: python

   cctx = zstandard.ZstdCompressor(level=10)
   compressor = cctx.stream_writer(fh)

   compressor.write(b'chunk 0\n')
   compressor.write(b'chunk 1\n')
   compressor.flush()
   # Receiver will be able to decode ``chunk 0\nchunk 1\n`` at this point.
   # Receiver is also expecting more data in the zstd *frame*.

   compressor.write(b'chunk 2\n')
   compressor.flush(zstandard.FLUSH_FRAME)
   # Receiver will be able to decode ``chunk 0\nchunk 1\nchunk 2``.
   # Receiver is expecting no more data, as the zstd frame is closed.
   # Any future calls to ``write()`` at this point will construct a new
   # zstd frame.

Instances can be used as context managers. Exiting the context manager is
the equivalent of calling ``close()``, which is equivalent to calling
``flush(zstandard.FLUSH_FRAME)``:

.. code-block:: python

   cctx = zstandard.ZstdCompressor(level=10)
   with cctx.stream_writer(fh) as compressor:
       compressor.write(b'chunk 0')
       compressor.write(b'chunk 1')
       ...

.. important::

   If ``flush(FLUSH_FRAME)`` is not called, emitted data doesn't constitute
   a full zstd *frame* and consumers of this data may complain about malformed
   input. It is recommended to use instances as a context manager to ensure
   *frames* are properly finished.

If the size of the data being fed to this streaming compressor is known,
you can declare it before compression begins:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   with cctx.stream_writer(fh, size=data_len) as compressor:
       compressor.write(chunk0)
       compressor.write(chunk1)
       ...

Declaring the size of the source data allows compression parameters to
be tuned. And if ``write_content_size`` is used, it also results in the
content size being written into the frame header of the output data.

The size of chunks being ``write()`` to the destination can be specified::

    cctx = zstandard.ZstdCompressor()
    with cctx.stream_writer(fh, write_size=32768) as compressor:
        ...

To see how much memory is being used by the streaming compressor::

    cctx = zstandard.ZstdCompressor()
    with cctx.stream_writer(fh) as compressor:
        ...
        byte_size = compressor.memory_size()

Thte total number of bytes written so far are exposed via ``tell()``::

    cctx = zstandard.ZstdCompressor()
    with cctx.stream_writer(fh) as compressor:
        ...
        total_written = compressor.tell()

``stream_writer()`` accepts a ``write_return_read`` boolean argument to control
the return value of ``write()``. When ``False`` (the default), ``write()`` returns
the number of bytes that were ``write()``en to the underlying object. When
``True``, ``write()`` returns the number of bytes read from the input that
were subsequently written to the compressor. ``True`` is the *proper* behavior
for ``write()`` as specified by the ``io.RawIOBase`` interface and will become
the default value in a future release.

The ``closefd`` keyword argument defines whether to close the underlying stream
when this instance is itself ``close()``d. The default is ``True``.

Streaming Output API
====================

``read_to_iter(reader)`` provides a mechanism to stream data out of a
compressor as an iterator of data chunks.:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
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

Like ``stream_writer()``, ``read_to_iter()`` also accepts a ``size`` argument
declaring the size of the input stream:

.. code-block:: python

    cctx = zstandard.ZstdCompressor()
    for chunk in cctx.read_to_iter(fh, size=some_int):
        pass

You can also control the size that data is ``read()`` from the source and
the ideal size of output chunks:

.. code-block:: python

    cctx = zstandard.ZstdCompressor()
    for chunk in cctx.read_to_iter(fh, read_size=16384, write_size=8192):
        pass

Unlike ``stream_writer()``, ``read_to_iter()`` does not give direct control
over the sizes of chunks fed into the compressor. Instead, chunk sizes will
be whatever the object being read from delivers. These will often be of a
uniform size.

Stream Copying API
==================

``copy_stream(ifh, ofh)`` can be used to copy data between 2 streams while
compressing it.:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   cctx.copy_stream(ifh, ofh)

For example, say you wish to compress a file:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   with open(input_path, 'rb') as ifh, open(output_path, 'wb') as ofh:
       cctx.copy_stream(ifh, ofh)

It is also possible to declare the size of the source stream:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   cctx.copy_stream(ifh, ofh, size=len_of_input)

You can also specify how large the chunks that are ``read()`` and ``write()``
from and to the streams:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   cctx.copy_stream(ifh, ofh, read_size=32768, write_size=16384)

The stream copier returns a 2-tuple of bytes read and written:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   read_count, write_count = cctx.copy_stream(ifh, ofh)

Compressor Interface
====================

``compressobj()`` returns an object that exposes ``compress(data)`` and
``flush()`` methods. Each returns compressed data or an empty bytes.

The purpose of ``compressobj()`` is to provide an API-compatible interface
with ``zlib.compressobj``, ``bz2.BZ2Compressor``, etc. This allows callers to
swap in different compressor objects while using the same API.

``flush()`` accepts an optional argument indicating how to end the stream.
``zstandard.COMPRESSOBJ_FLUSH_FINISH`` (the default) ends the compression stream.
Once this type of flush is performed, ``compress()`` and ``flush()`` can
no longer be called. This type of flush **must** be called to end the
compression context. If not called, returned data may be incomplete.

A ``zstandard.COMPRESSOBJ_FLUSH_BLOCK`` argument to ``flush()`` will flush a
zstd block. Flushes of this type can be performed multiple times. The next
call to ``compress()`` will begin a new zstd block.

Here is how this API should be used:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   cobj = cctx.compressobj()
   data = cobj.compress(b'raw input 0')
   data = cobj.compress(b'raw input 1')
   data = cobj.flush()

Or to flush blocks:

.. code-block:: python

   cctx.zstandard.ZstdCompressor()
   cobj = cctx.compressobj()
   data = cobj.compress(b'chunk in first block')
   data = cobj.flush(zstandard.COMPRESSOBJ_FLUSH_BLOCK)
   data = cobj.compress(b'chunk in second block')
   data = cobj.flush()

For best performance results, keep input chunks under 256KB. This avoids
extra allocations for a large output object.

It is possible to declare the input size of the data that will be fed into
the compressor:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   cobj = cctx.compressobj(size=6)
   data = cobj.compress(b'foobar')
   data = cobj.flush()

Chunker Interface
=================

``chunker(size=None, chunk_size=COMPRESSION_RECOMMENDED_OUTPUT_SIZE)`` returns
an object that can be used to iteratively feed chunks of data into a compressor
and produce output chunks of a uniform size.

The object returned by ``chunker()`` exposes the following methods:

``compress(data)``
   Feeds new input data into the compressor.

``flush()``
   Flushes all data currently in the compressor.

``finish()``
   Signals the end of input data. No new data can be compressed after this
   method is called.

``compress()``, ``flush()``, and ``finish()`` all return an iterator of
``bytes`` instances holding compressed data. The iterator may be empty. Callers
MUST iterate through all elements of the returned iterator before performing
another operation on the object.

All chunks emitted by ``compress()`` will have a length of ``chunk_size``.

``flush()`` and ``finish()`` may return a final chunk smaller than
``chunk_size``.

Here is how the API should be used:

.. code-block:: python

   cctx = zstandard.ZstdCompressor()
   chunker = cctx.chunker(chunk_size=32768)

   with open(path, 'rb') as fh:
       while True:
           in_chunk = fh.read(32768)
           if not in_chunk:
               break

           for out_chunk in chunker.compress(in_chunk):
               # Do something with output chunk of size 32768.

       for out_chunk in chunker.finish():
           # Do something with output chunks that finalize the zstd frame.

The ``chunker()`` API is often a better alternative to ``compressobj()``.

``compressobj()`` will emit output data as it is available. This results in a
*stream* of output chunks of varying sizes. The consistency of the output chunk
size with ``chunker()`` is more appropriate for many usages, such as sending
compressed data to a socket.

``compressobj()`` may also perform extra memory reallocations in order to
dynamically adjust the sizes of the output chunks. Since ``chunker()`` output
chunks are all the same size (except for flushed or final chunks), there is
less memory allocation overhead.

Batch Compression API
=====================

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
