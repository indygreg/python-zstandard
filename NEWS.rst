===============
Version History
===============

1.0.0 (not yet released)
========================

Actions Blocking Release
------------------------

* compression and decompression APIs that support ``io.RawIOBase`` interface
  (#13).
* ``stream_writer()`` APIs should support ``io.RawIOBase`` interface.
* Properly handle non-blocking I/O and partial writes for objects implementing
  ``io.RawIOBase``.
* Make ``write_return_read=True`` the default for objects implementing
  ``io.RawIOBase``.
* Audit for consistent and proper behavior of ``flush()`` and ``close()`` for
  all objects implementing ``io.RawIOBase``. Is calling ``close()`` on
  wrapped stream acceptable, should ``__exit__`` always call ``close()``,
  should ``close()`` imply ``flush()``, etc.
* Consider making reads across frames configurable behavior.
* Refactor module names so C and CFFI extensions live under ``zstandard``
  package.
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
  require use of ``CompressionParameters``.
* Expose ``ZSTD_getFrameProgression()`` from more compressor types.
* Support modifying compression parameters mid operation when supported by
  zstd API.
* Expose ``ZSTD_CLEVEL_DEFAULT`` constant.
* Expose ``ZSTD_SRCSIZEHINT_{MIN,MAX}`` constants.
* Support ``ZSTD_p_forceAttachDict`` compression parameter.
* Support ``ZSTD_dictForceLoad`` dictionary compression parameter.
* Support ``ZSTD_c_targetCBlockSize`` compression parameter.
* Support ``ZSTD_c_literalCompressionMode`` compression parameter.
* Support ``ZSTD_c_srcSizeHint`` compression parameter.
* Use ``ZSTD_CCtx_getParameter()``/``ZSTD_CCtxParam_getParameter()`` for retrieving
  compression parameters.
* Consider exposing ``ZSTDMT_toFlushNow()``.
* Expose ``ZDICT_trainFromBuffer_fastCover()``,
  ``ZDICT_optimizeTrainFromBuffer_fastCover``.
* Expose ``ZSTD_Sequence`` struct and related ``ZSTD_getSequences()`` API.
* Expose and enforce ``ZSTD_minCLevel()`` for minimum compression level.
* Consider a ``chunker()`` API for decompression.
* Consider stats for ``chunker()`` API, including finding the last consumed
  offset of input data.
* Consider exposing ``ZSTD_cParam_getBounds()`` and
  ``ZSTD_dParam_getBounds()`` APIs.
* Consider controls over resetting compression contexts (session only, parameters,
  or session and parameters).
* Actually use the CFFI backend in fuzzing tests.

Other Actions Not Blocking Release
---------------------------------------

* Support for block compression APIs.
* API for ensuring max memory ceiling isn't exceeded.
* Move off nose for testing.

0.13.0 (released 2019-12-28)
============================

Changes
-------

* ``pytest-xdist`` ``pytest`` extension is now installed so tests can be
  run in parallel.
* CI now builds ``manylinux2010`` and ``manylinux2014`` binary wheels
  instead of a mix of ``manylinux2010`` and ``manylinux1``.
* Official support for Python 3.8 has been added.
* Bundled zstandard library upgraded from 1.4.3 to 1.4.4.
* Python code has been reformatted with black.

0.12.0 (released 2019-09-15)
============================

Backwards Compatibility Notes
-----------------------------

* Support for Python 3.4 has been dropped since Python 3.4 is no longer
  a supported Python version upstream. (But it will likely continue to
  work until Python 2.7 support is dropped and we port to Python 3.5+
  APIs.)

Bug Fixes
---------

* Fix ``ZstdDecompressor.__init__`` on 64-bit big-endian systems (#91).
* Fix memory leak in ``ZstdDecompressionReader.seek()`` (#82).

Changes
-------

* CI transitioned to Azure Pipelines (from AppVeyor and Travis CI).
* Switched to ``pytest`` for running tests (from ``nose``).
* Bundled zstandard library upgraded from 1.3.8 to 1.4.3.

0.11.1 (released 2019-05-14)
============================

* Fix memory leak in ``ZstdDecompressionReader.seek()`` (#82).

0.11.0 (released 2019-02-24)
============================

Backwards Compatibility Notes
-----------------------------

* ``ZstdDecompressor.read()`` now allows reading sizes of ``-1`` or ``0``
  and defaults to ``-1``, per the documented behavior of
  ``io.RawIOBase.read()``. Previously, we required an argument that was
  a positive value.
* The ``readline()``, ``readlines()``, ``__iter__``, and ``__next__`` methods
  of ``ZstdDecompressionReader()`` now raise ``io.UnsupportedOperation``
  instead of ``NotImplementedError``.
* ``ZstdDecompressor.stream_reader()`` now accepts a ``read_across_frames``
  argument. The default value will likely be changed in a future release
  and consumers are advised to pass the argument to avoid unwanted change
  of behavior in the future.
* ``setup.py`` now always disables the CFFI backend if the installed
  CFFI package does not meet the minimum version requirements. Before, it was
  possible for the CFFI backend to be generated and a run-time error to
  occur.
* In the CFFI backend, ``CompressionReader`` and ``DecompressionReader``
  were renamed to ``ZstdCompressionReader`` and ``ZstdDecompressionReader``,
  respectively so naming is identical to the C extension. This should have
  no meaningful end-user impact, as instances aren't meant to be
  constructed directly.
* ``ZstdDecompressor.stream_writer()`` now accepts a ``write_return_read``
  argument to control whether ``write()`` returns the number of bytes
  read from the source / written to the decompressor. It defaults to off,
  which preserves the existing behavior of returning the number of bytes
  emitted from the decompressor. The default will change in a future release
  so behavior aligns with the specified behavior of ``io.RawIOBase``.
* ``ZstdDecompressionWriter.__exit__`` now calls ``self.close()``. This
  will result in that stream plus the underlying stream being closed as
  well. If this behavior is not desirable, do not use instances as
  context managers.
* ``ZstdCompressor.stream_writer()`` now accepts a ``write_return_read``
  argument to control whether ``write()`` returns the number of bytes read
  from the source / written to the compressor. It defaults to off, which
  preserves the existing behavior of returning the number of bytes emitted
  from the compressor. The default will change in a future release so
  behavior aligns with the specified behavior of ``io.RawIOBase``.
* ``ZstdCompressionWriter.__exit__`` now calls ``self.close()``. This will
  result in that stream plus any underlying stream being closed as well. If
  this behavior is not desirable, do not use instances as context managers.
* ``ZstdDecompressionWriter`` no longer requires being used as a context
  manager (#57).
* ``ZstdCompressionWriter`` no longer requires being used as a context
  manager (#57).
* The ``overlap_size_log`` attribute on ``CompressionParameters`` instances
  has been deprecated and will be removed in a future release. The
  ``overlap_log`` attribute should be used instead.
* The ``overlap_size_log`` argument to ``CompressionParameters`` has been
  deprecated and will be removed in a future release. The ``overlap_log``
  argument should be used instead.
* The ``ldm_hash_every_log`` attribute on ``CompressionParameters`` instances
  has been deprecated and will be removed in a future release. The
  ``ldm_hash_rate_log`` attribute should be used instead.
* The ``ldm_hash_every_log`` argument to ``CompressionParameters`` has been
  deprecated and will be removed in a future release. The ``ldm_hash_rate_log``
  argument should be used instead.
* The ``compression_strategy`` argument to ``CompressionParameters`` has been
  deprecated and will be removed in a future release. The ``strategy``
  argument should be used instead.
* The ``SEARCHLENGTH_MIN`` and ``SEARCHLENGTH_MAX`` constants are deprecated
  and will be removed in a future release. Use ``MINMATCH_MIN`` and
  ``MINMATCH_MAX`` instead.
* The ``zstd_cffi`` module has been renamed to ``zstandard.cffi``. As had
  been documented in the ``README`` file since the ``0.9.0`` release, the
  module should not be imported directly at its new location. Instead,
  ``import zstandard`` to cause an appropriate backend module to be loaded
  automatically.

Bug Fixes
---------

* CFFI backend could encounter a failure when sending an empty chunk into
  ``ZstdDecompressionObj.decompress()``. The issue has been fixed.
* CFFI backend could encounter an error when calling
  ``ZstdDecompressionReader.read()`` if there was data remaining in an
  internal buffer. The issue has been fixed. (#71)

Changes
-------

* ``ZstDecompressionObj.decompress()`` now properly handles empty inputs in
  the CFFI backend.
* ``ZstdCompressionReader`` now implements ``read1()`` and ``readinto1()``.
  These are part of the ``io.BufferedIOBase`` interface.
* ``ZstdCompressionReader`` has gained a ``readinto(b)`` method for reading
  compressed output into an existing buffer.
* ``ZstdCompressionReader.read()`` now defaults to ``size=-1`` and accepts
  read sizes of ``-1`` and ``0``. The new behavior aligns with the documented
  behavior of ``io.RawIOBase``.
* ``ZstdCompressionReader`` now implements ``readall()``. Previously, this
  method raised ``NotImplementedError``.
* ``ZstdDecompressionReader`` now implements ``read1()`` and ``readinto1()``.
  These are part of the ``io.BufferedIOBase`` interface.
* ``ZstdDecompressionReader.read()`` now defaults to ``size=-1`` and accepts
  read sizes of ``-1`` and ``0``. The new behavior aligns with the documented
  behavior of ``io.RawIOBase``.
* ``ZstdDecompressionReader()`` now implements ``readall()``. Previously, this
  method raised ``NotImplementedError``.
* The ``readline()``, ``readlines()``, ``__iter__``, and ``__next__`` methods
  of ``ZstdDecompressionReader()`` now raise ``io.UnsupportedOperation``
  instead of ``NotImplementedError``. This reflects a decision to never
  implement text-based I/O on (de)compressors and keep the low-level API
  operating in the binary domain. (#13)
* ``README.rst`` now documented how to achieve linewise iteration using
  an ``io.TextIOWrapper`` with a ``ZstdDecompressionReader``.
* ``ZstdDecompressionReader`` has gained a ``readinto(b)`` method for
  reading decompressed output into an existing buffer. This allows chaining
  to an ``io.TextIOWrapper`` on Python 3 without using an ``io.BufferedReader``.
* ``ZstdDecompressor.stream_reader()`` now accepts a ``read_across_frames``
  argument to control behavior when the input data has multiple zstd
  *frames*. When ``False`` (the default for backwards compatibility), a
  ``read()`` will stop when the end of a zstd *frame* is encountered. When
  ``True``, ``read()`` can potentially return data spanning multiple zstd
  *frames*. The default will likely be changed to ``True`` in a future
  release.
* ``setup.py`` now performs CFFI version sniffing and disables the CFFI
  backend if CFFI is too old. Previously, we only used ``install_requires``
  to enforce the CFFI version and not all build modes would properly enforce
  the minimum CFFI version. (#69)
* CFFI's ``ZstdDecompressionReader.read()`` now properly handles data
  remaining in any internal buffer. Before, repeated ``read()`` could
  result in *random* errors. (#71)
* Upgraded various Python packages in CI environment.
* Upgrade to hypothesis 4.5.11.
* In the CFFI backend, ``CompressionReader`` and ``DecompressionReader``
  were renamed to ``ZstdCompressionReader`` and ``ZstdDecompressionReader``,
  respectively.
* ``ZstdDecompressor.stream_writer()`` now accepts a ``write_return_read``
  argument to control whether ``write()`` returns the number of bytes read
  from the source. It defaults to ``False`` to preserve backwards
  compatibility.
* ``ZstdDecompressor.stream_writer()`` now implements the ``io.RawIOBase``
  interface and behaves as a proper stream object.
* ``ZstdCompressor.stream_writer()`` now accepts a ``write_return_read``
  argument to control whether ``write()`` returns the number of bytes read
  from the source. It defaults to ``False`` to preserve backwards
  compatibility.
* ``ZstdCompressionWriter`` now implements the ``io.RawIOBase`` interface and
  behaves as a proper stream object. ``close()`` will now close the stream
  and the underlying stream (if possible). ``__exit__`` will now call
  ``close()``. Methods like ``writable()`` and ``fileno()`` are implemented.
* ``ZstdDecompressionWriter`` no longer must be used as a context manager.
* ``ZstdCompressionWriter`` no longer must be used as a context manager.
  When not using as a context manager, it is important to call
  ``flush(FRAME_FRAME)`` or the compression stream won't be properly
  terminated and decoders may complain about malformed input.
* ``ZstdCompressionWriter.flush()`` (what is returned from
  ``ZstdCompressor.stream_writer()``) now accepts an argument controlling the
  flush behavior. Its value can be one of the new constants
  ``FLUSH_BLOCK`` or ``FLUSH_FRAME``.
* ``ZstdDecompressionObj`` instances now have a ``flush([length=None])`` method.
  This provides parity with standard library equivalent types. (#65)
* ``CompressionParameters`` no longer redundantly store individual compression
  parameters on each instance. Instead, compression parameters are stored inside
  the underlying ``ZSTD_CCtx_params`` instance. Attributes for obtaining
  parameters are now properties rather than instance variables.
* Exposed the ``STRATEGY_BTULTRA2`` constant.
* ``CompressionParameters`` instances now expose an ``overlap_log`` attribute.
  This behaves identically to the ``overlap_size_log`` attribute.
* ``CompressionParameters()`` now accepts an ``overlap_log`` argument that
  behaves identically to the ``overlap_size_log`` argument. An error will be
  raised if both arguments are specified.
* ``CompressionParameters`` instances now expose an ``ldm_hash_rate_log``
  attribute. This behaves identically to the ``ldm_hash_every_log`` attribute.
* ``CompressionParameters()`` now accepts a ``ldm_hash_rate_log`` argument that
  behaves identically to the ``ldm_hash_every_log`` argument. An error will be
  raised if both arguments are specified.
* ``CompressionParameters()`` now accepts a ``strategy`` argument that behaves
  identically to the ``compression_strategy`` argument. An error will be raised
  if both arguments are specified.
* The ``MINMATCH_MIN`` and ``MINMATCH_MAX`` constants were added. They are
  semantically equivalent to the old ``SEARCHLENGTH_MIN`` and
  ``SEARCHLENGTH_MAX`` constants.
* Bundled zstandard library upgraded from 1.3.7 to 1.3.8.
* ``setup.py`` denotes support for Python 3.7 (Python 3.7 was supported and
  tested in the 0.10 release).
* ``zstd_cffi`` module has been renamed to ``zstandard.cffi``.
* ``ZstdCompressor.stream_writer()`` now reuses a buffer in order to avoid
  allocating a new buffer for every operation. This should result in faster
  performance in cases where ``write()`` or ``flush()`` are being called
  frequently. (#62)
* Bundled zstandard library upgraded from 1.3.6 to 1.3.7.

0.10.2 (released 2018-11-03)
============================

Bug Fixes
---------

* ``zstd_cffi.py`` added to ``setup.py`` (#60).

Changes
-------

* Change some integer casts to avoid ``ssize_t`` (#61).

0.10.1 (released 2018-10-08)
============================

Backwards Compatibility Notes
-----------------------------

* ``ZstdCompressor.stream_reader().closed`` is now a property instead of a
  method (#58).
* ``ZstdDecompressor.stream_reader().closed`` is now a property instead of a
  method (#58).

Changes
-------

* Stop attempting to package Python 3.6 for Miniconda. The latest version of
  Miniconda is using Python 3.7. The Python 3.6 Miniconda packages were a lie
  since this were built against Python 3.7.
* ``ZstdCompressor.stream_reader()``'s and ``ZstdDecompressor.stream_reader()``'s
  ``closed`` attribute is now a read-only property instead of a method. This now
  properly matches the ``IOBase`` API and allows instances to be used in more
  places that accept ``IOBase`` instances.

0.10.0 (released 2018-10-08)
============================

Backwards Compatibility Notes
-----------------------------

* ``ZstdDecompressor.stream_reader().read()`` now consistently requires an
  argument in both the C and CFFI backends. Before, the CFFI implementation
  would assume a default value of ``-1``, which was later rejected.
* The ``compress_literals`` argument and attribute has been removed from
  ``zstd.ZstdCompressionParameters`` because it was removed by the zstd 1.3.5
  API.
* ``ZSTD_CCtx_setParametersUsingCCtxParams()`` is no longer called on every
  operation performed against ``ZstdCompressor`` instances. The reason for this
  change is that the zstd 1.3.5 API no longer allows this without calling
  ``ZSTD_CCtx_resetParameters()`` first. But if we called
  ``ZSTD_CCtx_resetParameters()`` on every operation, we'd have to redo
  potentially expensive setup when using dictionaries. We now call
  ``ZSTD_CCtx_reset()`` on every operation and don't attempt to change
  compression parameters.
* Objects returned by ``ZstdCompressor.stream_reader()`` no longer need to be
  used as a context manager. The context manager interface still exists and its
  behavior is unchanged.
* Objects returned by ``ZstdDecompressor.stream_reader()`` no longer need to be
  used as a context manager. The context manager interface still exists and its
  behavior is unchanged.

Bug Fixes
---------

* ``ZstdDecompressor.decompressobj().decompress()`` should now return all data
  from internal buffers in more scenarios. Before, it was possible for data to
  remain in internal buffers. This data would be emitted on a subsequent call
  to ``decompress()``. The overall output stream would still be valid. But if
  callers were expecting input data to exactly map to output data (say the
  producer had used ``flush(COMPRESSOBJ_FLUSH_BLOCK)`` and was attempting to
  map input chunks to output chunks), then the previous behavior would be
  wrong. The new behavior is such that output from
  ``flush(COMPRESSOBJ_FLUSH_BLOCK)`` fed into ``decompressobj().decompress()``
  should produce all available compressed input.
* ``ZstdDecompressor.stream_reader().read()`` should no longer segfault after
  a previous context manager resulted in error (#56).
* ``ZstdCompressor.compressobj().flush(COMPRESSOBJ_FLUSH_BLOCK)`` now returns
  all data necessary to flush a block. Before, it was possible for the
  ``flush()`` to not emit all data necessary to fully represent a block. This
  would mean decompressors wouldn't be able to decompress all data that had been
  fed into the compressor and ``flush()``ed. (#55).

New Features
------------

* New module constants ``BLOCKSIZELOG_MAX``, ``BLOCKSIZE_MAX``,
  ``TARGETLENGTH_MAX`` that expose constants from libzstd.
* New ``ZstdCompressor.chunker()`` API for manually feeding data into a
  compressor and emitting chunks of a fixed size. Like ``compressobj()``, the
  API doesn't impose restrictions on the input or output types for the
  data streams. Unlike ``compressobj()``, it ensures output chunks are of a
  fixed size. This makes this API useful when the compressed output is being
  fed into an I/O layer, where uniform write sizes are useful.
* ``ZstdCompressor.stream_reader()`` no longer needs to be used as a context
  manager (#34).
* ``ZstdDecompressor.stream_reader()`` no longer needs to be used as a context
  manager (#34).
* Bundled zstandard library upgraded from 1.3.4 to 1.3.6.

Changes
-------

* Added ``zstd_cffi.py`` and ``NEWS.rst`` to ``MANIFEST.in``.
* ``zstandard.__version__`` is now defined (#50).
* Upgrade pip, setuptools, wheel, and cibuildwheel packages to latest versions.
* Upgrade various packages used in CI to latest versions. Notably tox (in
  order to support Python 3.7).
* Use relative paths in setup.py to appease Python 3.7 (#51).
* Added CI for Python 3.7.

0.9.1 (released 2018-06-04)
===========================

* Debian packaging support.
* Fix typo in setup.py (#44).
* Support building with mingw compiler (#46).

0.9.0 (released 2018-04-08)
===========================

Backwards Compatibility Notes
-----------------------------

* CFFI 1.11 or newer is now required (previous requirement was 1.8).
* The primary module is now ``zstandard``. Please change imports of ``zstd``
  and ``zstd_cffi`` to ``import zstandard``. See the README for more. Support
  for importing the old names will be dropped in the next release.
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
* ``TARGETLENGTH_MAX`` constant has been removed (it disappeared from zstandard
  1.3.4).
* ``ZstdCompressor.write_to()`` and ``ZstdDecompressor.write_to()`` have been
  renamed to ``ZstdCompressor.stream_writer()`` and
  ``ZstdDecompressor.stream_writer()``, respectively. The old names are still
  aliased, but will be removed in the next major release.
* Content sizes are written into frame headers by default
  (``ZstdCompressor(write_content_size=True)`` is now the default).
* ``CompressionParameters`` has been renamed to ``ZstdCompressionParameters``
  for consistency with other types. The old name is an alias and will be removed
  in the next major release.

Bug Fixes
---------

* Fixed memory leak in ``ZstdCompressor.copy_stream()`` (#40) (from 0.8.2).
* Fixed memory leak in ``ZstdDecompressor.copy_stream()`` (#35) (from 0.8.2).
* Fixed memory leak of ``ZSTD_DDict`` instances in CFFI's ``ZstdDecompressor``.

New Features
------------

* Bundled zstandard library upgraded from 1.1.3 to 1.3.4. This delivers various
  bug fixes and performance improvements. It also gives us access to newer
  features.
* Support for negative compression levels.
* Support for *long distance matching* (facilitates compression ratios that approach
  LZMA).
* Supporting for reading empty zstandard frames (with an embedded content size
  of 0).
* Support for writing and partial support for reading zstandard frames without a
  magic header.
* New ``stream_reader()`` API that exposes the ``io.RawIOBase`` interface (allows
  you to ``.read()`` from a file-like object).
* Several minor features, bug fixes, and performance enhancements.
* Wheels for Linux and macOS are now provided with releases.

Changes
-------

* Functions accepting bytes data now use the buffer protocol and can accept
  more types (like ``memoryview`` and ``bytearray``) (#26).
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
* Vendored version of zstd upgraded to 1.3.4.
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
* ``ZstdCompressionDict.__init__`` now accepts a ``dict_type`` argument that
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
* Removed ``TARGETLENGTH_MAX`` constant.
* Added ``frame_header_size(data)`` function.
* Added ``frame_content_size(data)`` function.
* Consumers of ``ZSTD_decompress*`` have been switched to the new *advanced
  decompression* API.
* ``ZstdCompressor`` and ``ZstdCompressionParams`` can now be constructed with
  negative compression levels.
* ``ZstdDecompressor`` now accepts a ``max_window_size`` argument to limit the
  amount of memory required for decompression operations.
* ``FORMAT_ZSTD1`` and ``FORMAT_ZSTD1_MAGICLESS`` constants to be used with
  the ``format`` compression parameter to control whether the frame magic
  header is written.
* ``ZstdDecompressor`` now accepts a ``format`` argument to control the
  expected frame format.
* ``ZstdCompressor`` now has a ``frame_progression()`` method to return
  information about the current compression operation.
* Error messages in CFFI no longer have ``b''`` literals.
* Compiler warnings and underlying overflow issues on 32-bit platforms have been
  fixed.
* Builds in CI now build with compiler warnings as errors. This should hopefully
  fix new compiler warnings from being introduced.
* Make ``ZstdCompressor(write_content_size=True)`` and
  ``CompressionParameters(write_content_size=True)`` the default.
* ``CompressionParameters`` has been renamed to ``ZstdCompressionParameters``.

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
