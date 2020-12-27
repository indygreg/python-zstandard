.. _misc_apis:

==================
Miscellaneous APIs
==================

Frame Inspection
================

Data emitted from zstd compression is encapsulated in a *frame*. This frame
begins with a 4 byte *magic number* header followed by 2 to 14 bytes describing
the frame in more detail. For more info, see
https://github.com/facebook/zstd/blob/master/doc/zstd_compression_format.md.

``zstandard.get_frame_parameters(data)`` parses a zstd *frame* header from a
bytes instance and return a ``FrameParameters`` object describing the frame.

Depending on which fields are present in the frame and their values, the
length of the frame parameters varies. If insufficient bytes are passed
in to fully parse the frame parameters, ``ZstdError`` is raised. To ensure
frame parameters can be parsed, pass in at least 18 bytes.

``FrameParameters`` instances have the following attributes:

``content_size``
   Integer size of original, uncompressed content. This will be ``0`` if the
   original content size isn't written to the frame (controlled with the
   ``write_content_size`` argument to ``ZstdCompressor``) or if the input
   content size was ``0``.

``window_size``
   Integer size of maximum back-reference distance in compressed data.

``dict_id``
   Integer of dictionary ID used for compression. ``0`` if no dictionary
   ID was used or if the dictionary ID was ``0``.

``has_checksum``
   Bool indicating whether a 4 byte content checksum is stored at the end
   of the frame.

``zstandard.frame_header_size(data)`` returns the size of the zstandard frame
header.

``zstandard.frame_content_size(data)`` returns the content size as parsed from
the frame header. ``-1`` means the content size is unknown. ``0`` means
an empty frame. The content size is usually correct. However, it may not
be accurate.

estimate_decompression_context_size()
=====================================

Estimate the memory size requirements for a decompressor instance.

open()
======

Create a file object with zstandard (de)compression.

This function accepts the following arguments:

``filename``
   ``bytes``, ``str``, or ``os.PathLike`` defining a file to open or a
   file object (with a ``read()`` or ``write()`` method).

``mode``
   ``str`` File open mode. Accepts any of the open modes recognized by
   ``open()``.

``cctx``
   ``ZstdCompressor`` to use for compression. If not specified and file
   is opened for writing, the default ``ZstdCompressor`` will be used.

``dctx``
   ``ZstdDecompressor`` to use for decompression. If not specified and file
   is opened for reading, the default ``ZstdDecompressor`` will be used.

``encoding``, ``errors``, ``newline``
   ``str`` that define text encoding/decoding settings when the file is
   opened in text mode.

``closefd``
   ``bool`` whether to close the file when the returned object is closed.
    Only used if a file object is passed. If a filename is specified, the
    opened file is always closed when the returned object is closed.

The object returned from this function will be a ``ZstdDecompressionReader``
if opened for reading in binary mode, a ``ZstdCompressionWriter`` if opened
for writing in binary mode, or an ``io.TextIOWrapper`` if opened for reading
or writing in text mode.

Constants
=========

The following module constants/attributes are exposed:

``ZSTD_VERSION``
    This module attribute exposes a 3-tuple of the Zstandard version. e.g.
    ``(1, 0, 0)``

``MAX_COMPRESSION_LEVEL``
    Integer max compression level accepted by compression functions

``COMPRESSION_RECOMMENDED_INPUT_SIZE``
    Recommended chunk size to feed to compressor functions

``COMPRESSION_RECOMMENDED_OUTPUT_SIZE``
    Recommended chunk size for compression output

``DECOMPRESSION_RECOMMENDED_INPUT_SIZE``
    Recommended chunk size to feed into decompresor functions

``DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE``
    Recommended chunk size for decompression output

``FRAME_HEADER``
    bytes containing header of the Zstandard frame

``MAGIC_NUMBER``
    Frame header as an integer

``FLUSH_BLOCK``
    Flushing behavior that denotes to flush a zstd block. A decompressor will
    be able to decode all data fed into the compressor so far.

``FLUSH_FRAME``
    Flushing behavior that denotes to end a zstd frame. Any new data fed
    to the compressor will start a new frame.

``CONTENTSIZE_UNKNOWN``
    Value for content size when the content size is unknown.

``CONTENTSIZE_ERROR``
    Value for content size when content size couldn't be determined.

``WINDOWLOG_MIN``
    Minimum value for compression parameter

``WINDOWLOG_MAX``
    Maximum value for compression parameter

``CHAINLOG_MIN``
    Minimum value for compression parameter

``CHAINLOG_MAX``
    Maximum value for compression parameter

``HASHLOG_MIN``
    Minimum value for compression parameter

``HASHLOG_MAX``
    Maximum value for compression parameter

``SEARCHLOG_MIN``
    Minimum value for compression parameter

``SEARCHLOG_MAX``
    Maximum value for compression parameter

``MINMATCH_MIN``
    Minimum value for compression parameter

``MINMATCH_MAX``
    Maximum value for compression parameter

``SEARCHLENGTH_MIN``
    Minimum value for compression parameter

    Deprecated: use ``MINMATCH_MIN``

``SEARCHLENGTH_MAX``
    Maximum value for compression parameter

    Deprecated: use ``MINMATCH_MAX``

``TARGETLENGTH_MIN``
    Minimum value for compression parameter

``STRATEGY_FAST``
    Compression strategy

``STRATEGY_DFAST``
    Compression strategy

``STRATEGY_GREEDY``
    Compression strategy

``STRATEGY_LAZY``
    Compression strategy

``STRATEGY_LAZY2``
    Compression strategy

``STRATEGY_BTLAZY2``
    Compression strategy

``STRATEGY_BTOPT``
    Compression strategy

``STRATEGY_BTULTRA``
    Compression strategy

``STRATEGY_BTULTRA2``
    Compression strategy

``FORMAT_ZSTD1``
    Zstandard frame format

``FORMAT_ZSTD1_MAGICLESS``
    Zstandard frame format without magic header
