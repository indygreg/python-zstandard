.. _compressionparameters:

=============================
``ZstdCompressionParameters``
=============================

Zstandard offers a high-level *compression level* that maps to lower-level
compression parameters. For many consumers, this numeric level is the only
compression setting you'll need to touch.

But for advanced use cases, it might be desirable to tweak these lower-level
settings.

The ``ZstdCompressionParameters`` type represents these low-level compression
settings.

.. autoclass:: zstandard.ZstdCompressionParameters
   :members:
   :undoc-members:
