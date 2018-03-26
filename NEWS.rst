===============
Version History
===============

1.0.0 (not yet released)
========================

Actions Blocking Release
------------------------

* Support for prefix dictionaries.
* Audit compression parameter order semantics (e.g. when to set LDM versus
  window log).
* Ensure contexts are reset automatically in case of error; implement tests for
  these scenarios.
* compression and decompression APIs that support ``io.rawIOBase`` interface
  (#13).
* Refactor module names so C and CFFI extensions live under ``zstandard``
  package.
* Overall API design review.
* Use Python allocator where possible.
* Figure out what to do about experimental APIs not implemented by CFFI.
* APIs for auto adjusting compression parameters based on input size. e.g.
  clamping the window log so it isn't too large for input.
* Consider allowing compressor and decompressor instances to be thread safe,
  support concurrent operations.
* Support for magic-less frames.
* Audit for complete flushing when ending compression streams.
* Deprecate legacy APIs.
* Audit for ability to control read/write sizes on all APIs.
* Switch to new advanced decompression API (blocked on zstd 1.3.4).
* Detect memory leaks via bench.py.
* Remove low-level compression parameters from ``ZstdCompressor.__init__`` and
  require use of ``CompressionParameters``.

Other Actions Not Blocking Release
---------------------------------------

* Support for block compression APIs.
* API for ensuring max memory ceiling isn't exceeded.
* Move off nose for testing.
* Upgrade to latest hypothesis package and fix warnings.

0.9.0 (not yet released)
========================

Backwards Compatibility Notes
-----------------------------

* CFFI 1.10 or newer is now required (previous requirement was 1.8).
* The primary module is now ``zstandard``. Please change imports of ``zstd``
  and ``zstd_cffi`` to ``import zstandard``. See the README for more.
* ``ZstdCompressor.read_from()`` and ``ZstdDecompressor.read_from()`` have
  been renamed to ``read_to_iter()``. ``read_from()`` is aliased to the new
  name and will be deleted in a future release.
* Support for Python 2.6 has been removed.
* Support for Python 3.3 has been removed.
* The ``selectivity`` argument to ``train_dictionary()`` has been removed, as
  the feature disappeared from zstd 1.3.
* Support for legacy dictionaries has been removed. Cover dictionaries are now
  the default. ``train_cover_dictionary()`` has effectively been renamed to
  ``train_dictionary()``.
* The ``allow_empty`` argument from ``ZstdCompressor.compress()`` has been
  deleted and the method now allows empty inputs to be compressed by default.
* ``estimate_compression_context_size()`` has been removed. Use
  ``CompressionParameters.estimated_compression_context_size()`` instead.
* ``get_compression_parameters()`` has been removed. Use
  ``CompressionParameters.from_level()`` instead.
* The arguments to ``CompressionParameters.__init__()`` have changed. If you
  were using positional arguments before, the positions now map to different
  arguments. It is recommended to use keyword arguments to construct
  ``CompressionParameters`` instances.

Bug Fixes
---------

* Fixed memory leak in ``ZstdCompressor.copy_stream()`` (#40) (from 0.8.2).
* Fixed memory leak in ``ZstdDecompressor.copy_stream()`` (#35) (from 0.8.2).
* Fixed memory leak of ``ZSTD_DDict`` instances in CFFI's ``ZstdDecompressor``.

Changes
-------

* Functions accepting bytes data now use the buffer protocol and can accept
  more types (like ``memoryview`` and ``bytearray``) (#26).
* Updated vendored version of zstd to 1.2.0.
* Add #includes so compilation on OS X and BSDs works (#20).
* New ``ZstdDecompressor.stream_reader()`` API to obtain a read-only i/o stream
  of decompressed data for a source.
* New ``ZstdCompressor.stream_reader()`` API to obtain a read-only i/o stream of
  compressed data for a source.
* Renamed ``ZstdDecompressor.read_from()`` to ``ZstdDecompressor.read_to_iter()``.
  The old name is still available.
* Renamed ``ZstdCompressor.read_from()`` to ``ZstdCompressor.read_to_iter()``.
  ``read_from()`` is still available at its old location.
* Introduce the ``zstandard`` module to import and re-export the C or CFFI
  *backend* as appropriate. Behavior can be controlled via the
  ``PYTHON_ZSTANDARD_IMPORT_POLICY`` environment variable. See README for
  usage info.
* Vendored version of zstd upgraded to 1.3.3.
* Added module constants ``CONTENTSIZE_UNKNOWN`` and ``CONTENTSIZE_ERROR``.
* Add ``STRATEGY_BTULTRA`` compression strategy constant.
* Switch from deprecated ``ZSTD_getDecompressedSize()`` to
  ``ZSTD_getFrameContentSize()`` replacement.
* ``ZstdCompressor.compress()`` can now compress empty inputs without requiring
  special handling.
* ``ZstdCompressor`` and ``ZstdDecompressor`` now have a ``memory_size()``
  method for determining the current memory utilization of the underlying zstd
  primitive.
* ``train_dictionary()`` has new arguments and functionality for trying multiple
  variations of COVER parameters and selecting the best one.
* Added module constants ``LDM_MINMATCH_MIN``, ``LDM_MINMATCH_MAX``, and
  ``LDM_BUCKETSIZELOG_MAX``.
* Converted all consumers to the zstandard *new advanced API*, which uses
  ``ZSTD_compress_generic()``
* ``CompressionParameters.__init__`` now accepts several more arguments,
  including support for *long distance matching*.
* ``ZstdCompressionDict.__init__`` now accepts a ``dict_mode`` argument that
  controls how the dictionary should be interpreted. This can be used to
  force the use of *content-only* dictionaries or to require the presence
  of the dictionary magic header.
* ``ZstdCompressionDict.precompute_compress()`` can be used to precompute the
  compression dictionary so it can efficiently be used with multiple
  ``ZstdCompressor`` instances.
* Digested dictionaries are now stored in ``ZstdCompressionDict`` instances,
  created automatically on first use, and automatically reused by all
  ``ZstdDecompressor`` instances bound to that dictionary.
* All meaningful functions now accept keyword arguments.
* ``ZstdDecompressor.decompressobj()`` now accepts a ``write_size`` argument
  to control how much work to perform on every decompressor invocation.
* ``ZstdCompressor.write_to()`` now exposes a ``tell()``, which exposes the
  total number of bytes written so far.
* ``ZstdDecompressor.stream_reader()`` now supports ``seek()`` when moving
  forward in the stream.

0.8.2 (released 2018-02-22)
---------------------------

* Fixed memory leak in ``ZstdCompressor.copy_stream()`` (#40).
* Fixed memory leak in ``ZstdDecompressor.copy_stream()`` (#35).

0.8.1 (released 2017-04-08)
---------------------------

* Add #includes so compilation on OS X and BSDs works (#20).

0.8.0 (released 2017-03-08)
===========================

* CompressionParameters now has a estimated_compression_context_size() method.
  zstd.estimate_compression_context_size() is now deprecated and slated for
  removal.
* Implemented a lot of fuzzing tests.
* CompressionParameters instances now perform extra validation by calling
  ZSTD_checkCParams() at construction time.
* multi_compress_to_buffer() API for compressing multiple inputs as a
  single operation, as efficiently as possible.
* ZSTD_CStream instances are now used across multiple operations on
  ZstdCompressor instances, resulting in much better performance for
  APIs that do streaming.
* ZSTD_DStream instances are now used across multiple operations on
  ZstdDecompressor instances, resulting in much better performance for
  APIs that do streaming.
* train_dictionary() now releases the GIL.
* Support for training dictionaries using the COVER algorithm.
* multi_decompress_to_buffer() API for decompressing multiple frames as a
  single operation, as efficiently as possible.
* Support for multi-threaded compression.
* Disable deprecation warnings when compiling CFFI module.
* Fixed memory leak in train_dictionary().
* Removed DictParameters type.
* train_dictionary() now accepts keyword arguments instead of a
  DictParameters instance to control dictionary generation.

0.7.0 (released 2017-02-07)
===========================

* Added zstd.get_frame_parameters() to obtain info about a zstd frame.
* Added ZstdDecompressor.decompress_content_dict_chain() for efficient
  decompression of *content-only dictionary chains*.
* CFFI module fully implemented; all tests run against both C extension and
  CFFI implementation.
* Vendored version of zstd updated to 1.1.3.
* Use ZstdDecompressor.decompress() now uses ZSTD_createDDict_byReference()
  to avoid extra memory allocation of dict data.
* Add function names to error messages (by using ":name" in PyArg_Parse*
  functions).
* Reuse decompression context across operations. Previously, we created a
  new ZSTD_DCtx for each decompress(). This was measured to slow down
  decompression by 40-200MB/s. The API guarantees say ZstdDecompressor
  is not thread safe. So we reuse the ZSTD_DCtx across operations and make
  things faster in the process.
* ZstdCompressor.write_to()'s compress() and flush() methods now return number
  of bytes written.
* ZstdDecompressor.write_to()'s write() method now returns the number of bytes
  written to the underlying output object.
* CompressionParameters instances now expose their values as attributes.
* CompressionParameters instances no longer are subscriptable nor behave
  as tuples (backwards incompatible). Use attributes to obtain values.
* DictParameters instances now expose their values as attributes.

0.6.0 (released 2017-01-14)
===========================

* Support for legacy zstd protocols (build time opt in feature).
* Automation improvements to test against Python 3.6, latest versions
  of Tox, more deterministic AppVeyor behavior.
* CFFI "parser" improved to use a compiler preprocessor instead of rewriting
  source code manually.
* Vendored version of zstd updated to 1.1.2.
* Documentation improvements.
* Introduce a bench.py script for performing (crude) benchmarks.
* ZSTD_CCtx instances are now reused across multiple compress() operations.
* ZstdCompressor.write_to() now has a flush() method.
* ZstdCompressor.compressobj()'s flush() method now accepts an argument to
  flush a block (as opposed to ending the stream).
* Disallow compress(b'') when writing content sizes by default (issue #11).

0.5.2 (released 2016-11-12)
===========================

* more packaging fixes for source distribution

0.5.1 (released 2016-11-12)
===========================

* setup_zstd.py is included in the source distribution

0.5.0 (released 2016-11-10)
===========================

* Vendored version of zstd updated to 1.1.1.
* Continuous integration for Python 3.6 and 3.7
* Continuous integration for Conda
* Added compression and decompression APIs providing similar interfaces
  to the standard library ``zlib`` and ``bz2`` modules. This allows
  coding to a common interface.
* ``zstd.__version__` is now defined.
* ``read_from()`` on various APIs now accepts objects implementing the buffer
  protocol.
* ``read_from()`` has gained a ``skip_bytes`` argument. This allows callers
  to pass in an existing buffer with a header without having to create a
  slice or a new object.
* Implemented ``ZstdCompressionDict.as_bytes()``.
* Python's memory allocator is now used instead of ``malloc()``.
* Low-level zstd data structures are reused in more instances, cutting down
  on overhead for certain operations.
* ``distutils`` boilerplate for obtaining an ``Extension`` instance
  has now been refactored into a standalone ``setup_zstd.py`` file. This
  allows other projects with ``setup.py`` files to reuse the
  ``distutils`` code for this project without copying code.
* The monolithic ``zstd.c`` file has been split into a header file defining
  types and separate ``.c`` source files for the implementation.

Older History
=============

2016-08-31 - Zstandard 1.0.0 is released and Gregory starts hacking on a
Python extension for use by the Mercurial project. A very hacky prototype
is sent to the mercurial-devel list for RFC.

2016-09-03 - Most functionality from Zstandard C API implemented. Source
code published on https://github.com/indygreg/python-zstandard. Travis-CI
automation configured. 0.0.1 release on PyPI.

2016-09-05 - After the API was rounded out a bit and support for Python
2.6 and 2.7 was added, version 0.1 was released to PyPI.

2016-09-05 - After the compressor and decompressor APIs were changed, 0.2
was released to PyPI.

2016-09-10 - 0.3 is released with a bunch of new features. ZstdCompressor
now accepts arguments controlling frame parameters. The source size can now
be declared when performing streaming compression. ZstdDecompressor.decompress()
is implemented. Compression dictionaries are now cached when using the simple
compression and decompression APIs. Memory size APIs added.
ZstdCompressor.read_from() and ZstdDecompressor.read_from() have been
implemented. This rounds out the major compression/decompression APIs planned
by the author.

2016-10-02 - 0.3.3 is released with a bug fix for read_from not fully
decoding a zstd frame (issue #2).

2016-10-02 - 0.4.0 is released with zstd 1.1.0, support for custom read and
write buffer sizes, and a few bug fixes involving failure to read/write
all data when buffer sizes were too small to hold remaining data.

2016-11-10 - 0.5.0 is released with zstd 1.1.1 and other enhancements.
