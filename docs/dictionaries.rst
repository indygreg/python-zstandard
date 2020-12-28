.. _dictionaries:

============
Dictionaries
============

``ZstdCompressionDict``
=======================

.. autoclass:: zstandard.ZstdCompressionDict
   :members:
   :undoc-members:

Training Dictionaries
=====================

Unless using *prefix* dictionaries, dictionary data is produced by *training*
on existing data using the ``train_dictionary()`` function.

.. autofunction:: zstandard.train_dictionary
