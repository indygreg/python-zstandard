.. _compressionparameters:

==================================
``ZstdCompressionParameters`` Type
==================================

Zstandard offers a high-level *compression level* that maps to lower-level
compression parameters. For many consumers, this numeric level is the only
compression setting you'll need to touch.

But for advanced use cases, it might be desirable to tweak these lower-level
settings.

The ``ZstdCompressionParameters`` type represents these low-level compression
settings.

Instances of this type can be constructed from a myriad of keyword arguments
(defined below) for complete low-level control over each adjustable
compression setting.

From a higher level, one can construct a ``ZstdCompressionParameters`` instance
given a desired compression level and target input and dictionary size
using ``ZstdCompressionParameters.from_level()``. e.g.:

.. code-block:: python

    # Derive compression settings for compression level 7.
    params = zstandard.ZstdCompressionParameters.from_level(7)

    # With an input size of 1MB
    params = zstandard.ZstdCompressionParameters.from_level(7, source_size=1048576)

Using ``from_level()``, it is also possible to override individual compression
parameters or to define additional settings that aren't automatically derived.
e.g.:

.. code-block:: python

    params = zstandard.ZstdCompressionParameters.from_level(4, window_log=10)
    params = zstandard.ZstdCompressionParameters.from_level(5, threads=4)

Or you can define low-level compression settings directly:

.. code-block:: python

    params = zstandard.ZstdCompressionParameters(window_log=12, enable_ldm=True)

Once a ``ZstdCompressionParameters`` instance is obtained, it can be used to
configure a compressor:

.. code-block:: python

    cctx = zstandard.ZstdCompressor(compression_params=params)

The named arguments and attributes of ``ZstdCompressionParameters`` are as
follows:

* format
* compression_level
* window_log
* hash_log
* chain_log
* search_log
* min_match
* target_length
* strategy
* compression_strategy (deprecated: same as ``strategy``)
* write_content_size
* write_checksum
* write_dict_id
* job_size
* overlap_log
* force_max_window
* enable_ldm
* ldm_hash_log
* ldm_min_match
* ldm_bucket_size_log
* ldm_hash_rate_log
* ldm_hash_every_log (deprecated: same as ``ldm_hash_rate_log``)
* threads

Some of these are very low-level settings. It may help to consult the official
zstandard documentation for their behavior. Look for the ``ZSTD_p_*`` constants
in ``zstd.h`` (https://github.com/facebook/zstd/blob/dev/lib/zstd.h).
