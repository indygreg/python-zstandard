.. _compressor:

=======================
``ZstdCompressor`` Type
=======================

The ``zstandard.ZstdCompressor`` type provides an interface for performing
compression operations. Each instance is essentially a wrapper around a
``ZSTD_CCtx`` from the C API.

.. autoclass:: zstandard.ZstdCompressor
   :members:
   :undoc-members:
