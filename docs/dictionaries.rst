.. _dictionaries:

============
Dictionaries
============

``ZstdCompressionDict`` Type
============================

Compression dictionaries are represented by the ``ZstdCompressionDict`` type.

Instances can be constructed from bytes:

.. code-block:: python

   dict_data = zstandard.ZstdCompressionDict(data)

It is possible to construct a dictionary from *any* data. If the data doesn't
begin with a magic header, it will be treated as a *prefix* dictionary.
*Prefix* dictionaries allow compression operations to reference raw data
within the dictionary.

It is possible to force the use of *prefix* dictionaries or to require a
dictionary header:

.. code-block:: python

   dict_data = zstandard.ZstdCompressionDict(
       data, dict_type=zstandard.DICT_TYPE_RAWCONTENT)

   dict_data = zstandard.ZstdCompressionDict(
       data, dict_type=zstandard.DICT_TYPE_FULLDICT)

You can see how many bytes are in the dictionary by calling ``len()``:

.. code-block:: python

   dict_data = zstandard.train_dictionary(size, samples)
   dict_size = len(dict_data)  # will not be larger than ``size``

Once you have a dictionary, you can pass it to the objects performing
compression and decompression:

.. code-block:: python

   dict_data = zstandard.train_dictionary(131072, samples)

   cctx = zstandard.ZstdCompressor(dict_data=dict_data)
   for source_data in input_data:
       compressed = cctx.compress(source_data)
       # Do something with compressed data.

   dctx = zstandard.ZstdDecompressor(dict_data=dict_data)
   for compressed_data in input_data:
       buffer = io.BytesIO()
       with dctx.stream_writer(buffer) as decompressor:
           decompressor.write(compressed_data)
       # Do something with raw data in ``buffer``.

Dictionaries have unique integer IDs. You can retrieve this ID via:

.. code-block:: python

   dict_id = zstandard.dictionary_id(dict_data)

You can obtain the raw data in the dict (useful for persisting and constructing
a ``ZstdCompressionDict`` later) via ``as_bytes()``:

.. code-block:: python

   dict_data = zstandard.train_dictionary(size, samples)
   raw_data = dict_data.as_bytes()

By default, when a ``ZstdCompressionDict`` is *attached* to a
``ZstdCompressor``, each ``ZstdCompressor`` performs work to prepare the
dictionary for use. This is fine if only 1 compression operation is being
performed or if the ``ZstdCompressor`` is being reused for multiple operations.
But if multiple ``ZstdCompressor`` instances are being used with the dictionary,
this can add overhead.

It is possible to *precompute* the dictionary so it can readily be consumed
by multiple ``ZstdCompressor`` instances:

.. code-block:: python

    d = zstandard.ZstdCompressionDict(data)

    # Precompute for compression level 3.
    d.precompute_compress(level=3)

    # Precompute with specific compression parameters.
    params = zstandard.ZstdCompressionParameters(...)
    d.precompute_compress(compression_params=params)

.. note::

   When a dictionary is precomputed, the compression parameters used to
   precompute the dictionary overwrite some of the compression parameters
   specified to ``ZstdCompressor.__init__``.

Training Dictionaries
=====================

Unless using *prefix* dictionaries, dictionary data is produced by *training*
on existing data:

.. code-block:: python

   dict_data = zstandard.train_dictionary(size, samples)

This takes a target dictionary size and list of bytes instances and creates and
returns a ``ZstdCompressionDict``.

The dictionary training mechanism is known as *cover*. More details about it
are available in the paper *Effective Construction of Relative Lempel-Ziv
Dictionaries* (authors: Liao, Petri, Moffat, Wirth).

The cover algorithm takes parameters ``k` and ``d``. These are the
*segment size* and *dmer size*, respectively. The returned dictionary
instance created by this function has ``k`` and ``d`` attributes
containing the values for these parameters. If a ``ZstdCompressionDict``
is constructed from raw bytes data (a content-only dictionary), the
``k`` and ``d`` attributes will be ``0``.

The segment and dmer size parameters to the cover algorithm can either be
specified manually or ``train_dictionary()`` can try multiple values
and pick the best one, where *best* means the smallest compressed data size.
This later mode is called *optimization* mode.

Under the hood, this function always calls
``ZDICT_optimizeTrainFromBuffer_fastCover()``. See the corresponding C library
documentation for more.

If neither ``steps`` nor ``threads`` is defined, defaults for ``d``, ``steps``,
and ``level`` will be used that are equivalent with what
``ZDICT_trainFromBuffer()`` would use.

This function takes the following arguments:

dict_size
   Target size in bytes of the dictionary to generate.
samples
   A list of bytes holding samples the dictionary will be trained from.
k
   Segment size : constraint: 0 < k : Reasonable range [16, 2048+]
d
   dmer size : constraint: 0 < d <= k : Reasonable range [6, 16]
f
   log of size of frequency array : constraint: 0 < f <= 31 : 1 means
   default(20)
split_point
   Percentage of samples used for training: Only used for optimization.
   The first # samples * ``split_point`` samples will be used to training.
   The last # samples * (1 - split_point) samples will be used for testing.
   0 means default (0.75), 1.0 when all samples are used for both training
   and testing.
accel
   Acceleration level: constraint: 0 < accel <= 10. Higher means faster
   and less accurate, 0 means default(1).
dict_id
   Integer dictionary ID for the produced dictionary. Default is 0, which uses
   a random value.
steps
   Number of steps through ``k`` values to perform when trying parameter
   variations.
threads
   Number of threads to use when trying parameter variations. Default is 0,
   which means to use a single thread. A negative value can be specified to
   use as many threads as there are detected logical CPUs.
level
   Integer target compression level when trying parameter variations.
notifications
   Controls writing of informational messages to ``stderr``. ``0`` (the
   default) means to write nothing. ``1`` writes errors. ``2`` writes
   progression info. ``3`` writes more details. And ``4`` writes all info.
