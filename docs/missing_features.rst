==================================
Missing and Unimplemented Features
==================================

This document attempts to capture features of the zstd C API that are currently
not exposed to Python.

If there is a feature on this page that would be beneficial to you, please
open a GitHub issue requesting its implementation. If an existing GitHub
issue exists, please leave a comment on the issue to amplify the importance of
the request (this project's author doesn't monitor the emoji counts).

Missing Constants
=================

* ``ZSTD_CLEVEL_DEFAULT``
* ``ZSTD_SRCSIZEHINT_MIN``
* ``ZSTD_SRCSIZEHINT_MAX``
* ``ZSTD_BLOCKSIZE_MAX_MIN``
* ``ZSTD_DECOMPRESSION_MARGIN``

Compression and Decompression Parameters
========================================

* ``ZSTD_p_forceAttachDict``
* ``ZSTD_dictForceLoad``
* ``ZSTD_c_targetCBlockSize``
* ``ZSTD_c_literalCompressionMode``
* ``ZSTD_c_srcSizeHint``
* ``ZSTD_d_stableOutBuffer``
* ``ZSTD_c_enableDedicatedDictSearch``
* ``ZSTD_c_stableInBuffer``
* ``ZSTD_c_stableOutBuffer``
* ``ZSTD_c_blockDelimiters``
* ``ZSTD_c_validateSequences``
* ``ZSTD_c_useBlockSplitter``
* ``ZSTD_c_useRowMatchFinder``
* ``ZSTD_d_forceIgnoreChecksum``
* ``ZSTD_d_refMultipleDDicts``
* ``ZSTD_refMultipleDDicts_e``
* ``ZSTD_c_prefetchCDictTables``
* ``ZSTD_c_enableSeqProducerFallback``
* ``ZSTD_c_maxBlockSize``
* ``ZSTD_c_searchForExternalRepcodes``
* ``ZSTD_d_disableHuffmanAssembly``
* ``ZSTD_d_stableOutBuffer``

Missing Functions
=================

* ``ZSTDMT_toFlushNow()``
* ``ZSTD_minCLevel()``
* ``ZSTD_cParam_getBounds()``
* ``ZSTD_dParam_getBounds()``
* ``ZSTD_generateSequences()``
* ``ZSTD_mergeBlockDelimiters()``
* ``ZSTD_compressSequences()``
* ``ZSTD_writeSkippableFrame()``
* ``ZSTD_decompressionMargin()``
* ``ZSTD_sequenceBound()``

Missing Features
================

* ``ZSTD_getFrameProgression()`` isn't exposed everywhere it could be.
* Compression parameters cannot be modified mid operation.
* ``ZSTD_Sequence`` and related ``ZSTD_getSequences()`` not exposed.
* ``ZSTD_threadPool`` not exposed.
* ``ZSTD_sequenceProducer_F`` and ``ZSTD_registerSequenceProducer()`` not
  exposed.
* ``ZSTD_CCtx_getParameter()``, ``ZSTD_CCtxParam_getParameter()``, and
  ``ZSTD_DCtx_getParameter()`` could be leveraged for parameter retrieval.
* ``ZSTD_CCtx_setCParams()`` could potentially be utilized.
* ``ZSTD_error_*`` constants / error codes not exposed.

Potential 1.0 Release Features
==============================

The following track features and changes we would nominally perform
before a 1.0 release.

* Properly handle non-blocking I/O and partial writes for objects implementing
  ``io.RawIOBase``.
* Consider making reads across frames configurable behavior.
* Overall API design review.
* Use Python allocator where possible.
* Figure out what to do about experimental APIs not implemented by CFFI.
* APIs for auto adjusting compression parameters based on input size. e.g.
  clamping the window log so it isn't too large for input.
* Consider allowing compressor and decompressor instances to be thread safe,
  support concurrent operations. Or track when an operation is in progress and
  refuse to let concurrent operations use the same instance.
* Support for magic-less frames for all decompression operations (``decompress()``
  doesn't work due to sniffing the content size and the lack of a ZSTD API to
  sniff magic-less frames - this should be fixed in 1.3.5.).
* Audit for complete flushing when ending compression streams.
* Deprecate legacy APIs.
* Audit for ability to control read/write sizes on all APIs.
* Detect memory leaks via bench.py.
* Remove low-level compression parameters from ``ZstdCompressor.__init__`` and
  require use of ``ZstdCompressionParameters``.
* Consider a ``chunker()`` API for decompression.
* Consider stats for ``chunker()`` API, including finding the last consumed
  offset of input data.
* Consider controls over resetting compression contexts (session only, parameters,
  or session and parameters).
* Utilize ``ZSTD_getDictID_fromCDict()``?
* Stop relying on private libzstd headers and symbols (namely ``pool.h``).

And other non-essential features:

* Support for block compression APIs.
* API for ensuring max memory ceiling isn't exceeded.
* Move off nose for testing.
