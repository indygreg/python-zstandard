============
Buffer Types
============

The ``zstandard`` module exposes a handful of custom types for interfacing with
memory buffers. The primary goal of these types is to facilitate efficient
multi-object operations.

The essential idea is to have a single memory allocation provide backing
storage for multiple logical objects. This has 2 main advantages: fewer
allocations and optimal memory access patterns. This avoids having to allocate
a Python object for each logical object and furthermore ensures that access of
data for objects can be sequential (read: fast) in memory.

``BufferSegment``
=================

.. autoclass:: zstandard.BufferSegment
   :members:
   :undoc-members:

``BufferSegments``
==================

.. autoclass:: zstandard.BufferSegments
   :members:
   :undoc-members:

``BufferWithSegments``
======================

.. autoclass:: zstandard.BufferWithSegments
   :members:
   :undoc-members:

``BufferWithSegmentsCollection``
================================

.. autoclass:: zstandard.BufferWithSegmentsCollection
   :members:
   :undoc-members:
