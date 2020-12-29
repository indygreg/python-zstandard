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

.. autofunction:: zstandard.get_frame_parameters

.. autofunction:: zstandard.frame_header_size

.. autofunction:: zstandard.frame_content_size

.. autoclass:: zstandard.FrameParameters
   :members:
   :undoc-members:

``estimate_decompression_context_size()``
=========================================

.. autofunction:: zstandard.estimate_decompression_context_size

``open()``
==========

.. autofunction:: zstandard.open

``compress()``
==============

.. autofunction:: zstandard.compress

``decompress()``
================

.. autofunction:: zstandard.decompress

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
