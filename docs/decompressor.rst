.. _decompressor:

=========================
``ZstdDecompressor`` Type
=========================

The ``zstandard.ZstdDecompressor`` type provides an interface for performing
decompression. It is effectively a wrapper around the ``ZSTD_DCtx`` type from
the C API.

Instantiating
=============

Each instance is associated with parameters that control decompression. These
come from the following named arguments (all optional):

``dict_data``
   Compression dictionary to use.

``max_window_size``
   Sets an upper limit on the window size for decompression operations in
   kibibytes. This setting can be used to prevent large memory allocations
   for inputs using large compression windows.

``format``
   Set the format of data for the decoder. By default, this is
   ``zstandard.FORMAT_ZSTD1``. It can be set to
   ``zstandard.FORMAT_ZSTD1_MAGICLESS`` to allow decoding frames without the
   4 byte magic header. Not all decompression APIs support this mode.

The interface of this class is very similar to ``ZstdCompressor`` (by design).

Unless specified otherwise, assume that no two methods of ``ZstdDecompressor``
instances can be called from multiple Python threads simultaneously. In other
words, assume instances are not thread safe unless stated otherwise.

Utility Methods
===============

``memory_size()``
-----------------

Obtains the size of the underlying zstd decompression context, in bytes.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    size = dctx.memory_size()

One-Shot Decompression
======================

``decompress(data)`` can be used to decompress an entire compressed zstd
frame in a single operation.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    decompressed = dctx.decompress(data)

By default, ``decompress(data)`` will only work on data written with the content
size encoded in its header (this is the default behavior of
``ZstdCompressor().compress()`` but may not be true for streaming compression). If
compressed data without an embedded content size is seen, ``zstandard.ZstdError``
will be raised.

If the compressed data doesn't have its content size embedded within it,
decompression can be attempted by specifying the ``max_output_size``
argument.:

    dctx = zstandard.ZstdDecompressor()
    uncompressed = dctx.decompress(data, max_output_size=1048576)

Ideally, ``max_output_size`` will be identical to the decompressed output
size.

If ``max_output_size`` is too small to hold the decompressed data,
``zstandard.ZstdError`` will be raised.

If ``max_output_size`` is larger than the decompressed data, the allocated
output buffer will be resized to only use the space required.

Please note that an allocation of the requested ``max_output_size`` will be
performed every time the method is called. Setting to a very large value could
result in a lot of work for the memory allocator and may result in
``MemoryError`` being raised if the allocation fails.

.. important::

   If the exact size of decompressed data is unknown (not passed in explicitly
   and not stored in the zstandard frame), for performance reasons it is
   encouraged to use a streaming API.

Stream Reader Interface
=======================

``stream_reader(source)`` can be used to obtain an object conforming to the
``io.RawIOBase`` interface for reading decompressed output as a stream:

.. code-block:: python

   with open(path, 'rb') as fh:
       dctx = zstandard.ZstdDecompressor()
       reader = dctx.stream_reader(fh)
       while True:
           chunk = reader.read(16384)
            if not chunk:
                break

            # Do something with decompressed chunk.

The stream can also be used as a context manager:

.. code-block:: python

   with open(path, 'rb') as fh:
       dctx = zstandard.ZstdDecompressor()
       with dctx.stream_reader(fh) as reader:
           ...

When used as a context manager, the stream is closed and the underlying
resources are released when the context manager exits. Future operations against
the stream will fail.

The ``source`` argument to ``stream_reader()`` can be any object with a
``read(size)`` method or any object implementing the *buffer protocol*.

If the ``source`` is a stream, you can specify how large ``read()`` requests
to that stream should be via the ``read_size`` argument. It defaults to
``zstandard.DECOMPRESSION_RECOMMENDED_INPUT_SIZE``.:

.. code-block:: python

   with open(path, 'rb') as fh:
       dctx = zstandard.ZstdDecompressor()
       # Will perform fh.read(8192) when obtaining data for the decompressor.
       with dctx.stream_reader(fh, read_size=8192) as reader:
           ...

The stream returned by ``stream_reader()`` is not writable.

The stream returned by ``stream_reader()`` is *partially* seekable.
Absolute and relative positions (``SEEK_SET`` and ``SEEK_CUR``) forward
of the current position are allowed. Offsets behind the current read
position and offsets relative to the end of stream are not allowed and
will raise ``ValueError`` if attempted.

``tell()`` returns the number of decompressed bytes read so far.

Not all I/O methods are implemented. Notably missing is support for
``readline()``, ``readlines()``, and linewise iteration support. This is
because streams operate on binary data - not text data. If you want to
convert decompressed output to text, you can chain an ``io.TextIOWrapper``
to the stream:

.. code-block:: python

   with open(path, 'rb') as fh:
       dctx = zstandard.ZstdDecompressor()
       stream_reader = dctx.stream_reader(fh)
       text_stream = io.TextIOWrapper(stream_reader, encoding='utf-8')

       for line in text_stream:
           ...

The ``read_across_frames`` argument to ``stream_reader()`` controls the
behavior of read operations when the end of a zstd *frame* is encountered.
When ``False`` (the default), a read will complete when the end of a
zstd *frame* is encountered. When ``True``, a read can potentially
return data spanning multiple zstd *frames*.

The ``closefd`` keyword argument defines whether to close the underlying stream
when this instance is itself ``close()``d. The default is ``True``.

Streaming Writer Interface
==========================

``stream_writer(fh)`` allows you to *stream* data into a decompressor.

Returned instances implement the ``io.RawIOBase`` interface. Only methods
that involve writing will do useful things.

The argument to ``stream_writer()`` is typically an object that also implements
``io.RawIOBase``. But any object with a ``write(data)`` method will work. Many
common Python types conform to this interface, including open file handles
and ``io.BytesIO``.

Behavior is similar to ``ZstdCompressor.stream_writer()``: compressed data
is sent to the decompressor by calling ``write(data)`` and decompressed
output is written to the underlying stream by calling its ``write(data)``
method.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    decompressor = dctx.stream_writer(fh)

    decompressor.write(compressed_data)
    ...


Calls to ``write()`` will return the number of bytes written to the output
object. Not all inputs will result in bytes being written, so return values
of ``0`` are possible.

Like the ``stream_writer()`` compressor, instances can be used as context
managers. However, context managers add no extra special behavior and offer
little to no benefit to being used.

The ``closefd`` keyword argument defines whether to close the underlying stream
when this instance is itself ``close()``d. The default is ``True``.

Calling ``close()`` will mark the stream as closed and subsequent I/O operations
will raise ``ValueError`` (per the documented behavior of ``io.RawIOBase``).
``close()`` will also call ``close()`` on the underlying stream if such a
method exists and ``closefd`` is True.

The size of chunks being ``write()`` to the destination can be specified:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_writer(fh, write_size=16384) as decompressor:
        pass

You can see how much memory is being used by the decompressor:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_writer(fh) as decompressor:
        byte_size = decompressor.memory_size()

``stream_writer()`` accepts a ``write_return_read`` boolean argument to control
the return value of ``write()``. When ``False`` (the default)``, ``write()``
returns the number of bytes that were ``write()``en to the underlying stream.
When ``True``, ``write()`` returns the number of bytes read from the input.
``True`` is the *proper* behavior for ``write()`` as specified by the
``io.RawIOBase`` interface and will become the default in a future release.

Streaming Output API
====================

``read_to_iter(fh)`` provides a mechanism to stream decompressed data out of a
compressed source as an iterator of data chunks.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh):
        # Do something with original data.

``read_to_iter()`` accepts an object with a ``read(size)`` method that will
return  compressed bytes or an object conforming to the buffer protocol that
can expose its data as a contiguous range of bytes.

``read_to_iter()`` returns an iterator whose elements are chunks of the
decompressed data.

The size of requested ``read()`` from the source can be specified:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh, read_size=16384):
        pass

It is also possible to skip leading bytes in the input data:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    for chunk in dctx.read_to_iter(fh, skip_bytes=1):
        pass

.. tip::

   Skipping leading bytes is useful if the source data contains extra
   *header* data. Traditionally, you would need to create a slice or
   ``memoryview`` of the data you want to decompress. This would create
   overhead. It is more efficient to pass the offset into this API.

Similarly to ``ZstdCompressor.read_to_iter()``, the consumer of the iterator
controls when data is decompressed. If the iterator isn't consumed,
decompression is put on hold.

When ``read_to_iter()`` is passed an object conforming to the buffer protocol,
the behavior may seem similar to what occurs when the simple decompression
API is used. However, this API works when the decompressed size is unknown.
Furthermore, if feeding large inputs, the decompressor will work in chunks
instead of performing a single operation.

Stream Copying API
==================

``copy_stream(ifh, ofh)`` can be used to copy data across 2 streams while
performing decompression.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    dctx.copy_stream(ifh, ofh)

e.g. to decompress a file to another file:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    with open(input_path, 'rb') as ifh, open(output_path, 'wb') as ofh:
        dctx.copy_stream(ifh, ofh)

The size of chunks being ``read()`` and ``write()`` from and to the streams
can be specified:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    dctx.copy_stream(ifh, ofh, read_size=8192, write_size=16384)

Decompressor API
================

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

Here is how this API should be used:

.. code-block:: python

   dctx = zstandard.ZstdDecompressor()
   dobj = dctx.decompressobj()
   data = dobj.decompress(compressed_chunk_0)
   data = dobj.decompress(compressed_chunk_1)

By default, calls to ``decompress()`` write output data in chunks of size
``DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE``. These chunks are concatenated
before being returned to the caller. It is possible to define the size of
these temporary chunks by passing ``write_size`` to ``decompressobj()``:

.. code-block:: python

   dctx = zstandard.ZstdDecompressor()
   dobj = dctx.decompressobj(write_size=1048576)

.. note::

   Because calls to ``decompress()`` may need to perform multiple
   memory (re)allocations, this streaming decompression API isn't as
   efficient as other APIs.

For compatibility with the standard library APIs, instances expose a
``flush([length=None])`` method. This method no-ops and has no meaningful
side-effects, making it safe to call any time.

Batch Decompression API
=======================

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
inputs.:

.. code-block:: python

    dctx = zstandard.ZstdDecompressor()
    results = dctx.multi_decompress_to_buffer([b'...', b'...'])

The decompressed size of each frame MUST be discoverable. It can either be
embedded within the zstd frame (``write_content_size=True`` argument to
``ZstdCompressor``) or passed in via the ``decompressed_sizes`` argument.

The ``decompressed_sizes`` argument is an object conforming to the buffer
protocol which holds an array of 64-bit unsigned integers in the machine's
native format defining the decompressed sizes of each frame. If this argument
is passed, it avoids having to scan each frame for its decompressed size.
This frame scanning can add noticeable overhead in some scenarios.:

.. code-block:: python

    frames = [...]
    sizes = struct.pack('=QQQQ', len0, len1, len2, len3)

    dctx = zstandard.ZstdDecompressor()
    results = dctx.multi_decompress_to_buffer(frames, decompressed_sizes=sizes)

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
calls are avoided. This is ideal for scenarios where callers know up front that
they need to access data for multiple frames, such as when  *delta chains* are
being used.

Currently, the implementation always spawns multiple threads when requested,
even if the amount of work to do is small. In the future, it will be smarter
about avoiding threads and their associated overhead when the amount of
work to do is small.

Prefix Dictionary Chain Decompression
=====================================

``decompress_content_dict_chain(frames)`` performs decompression of a list of
zstd frames produced using chained *prefix* dictionary compression. Such
a list of frames is produced by compressing discrete inputs where each
non-initial input is compressed with a *prefix* dictionary consisting of the
content of the previous input.

For example, say you have the following inputs:

.. code-block:: python

   inputs = [b'input 1', b'input 2', b'input 3']

The zstd frame chain consists of:

1. ``b'input 1'`` compressed in standalone/discrete mode
2. ``b'input 2'`` compressed using ``b'input 1'`` as a *prefix* dictionary
3. ``b'input 3'`` compressed using ``b'input 2'`` as a *prefix* dictionary

Each zstd frame **must** have the content size written.

The following Python code can be used to produce a *prefix dictionary chain*:

.. code-block:: python

    def make_chain(inputs):
        frames = []

        # First frame is compressed in standalone/discrete mode.
        zctx = zstandard.ZstdCompressor()
        frames.append(zctx.compress(inputs[0]))

        # Subsequent frames use the previous fulltext as a prefix dictionary
        for i, raw in enumerate(inputs[1:]):
            dict_data = zstandard.ZstdCompressionDict(
                inputs[i], dict_type=zstandard.DICT_TYPE_RAWCONTENT)
            zctx = zstandard.ZstdCompressor(dict_data=dict_data)
            frames.append(zctx.compress(raw))

        return frames

``decompress_content_dict_chain()`` returns the uncompressed data of the last
element in the input chain.

.. note::

   It is possible to implement *prefix dictionary chain* decompression
   on top of other APIs. However, this function will likely be faster -
   especially for long input chains - as it avoids the overhead of instantiating
   and passing around intermediate objects between C and Python.
