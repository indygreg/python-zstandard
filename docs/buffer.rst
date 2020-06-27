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

``BufferWithSegments``
======================

The ``BufferWithSegments`` type represents a memory buffer containing N
discrete items of known lengths (segments). It is essentially a fixed size
memory address and an array of 2-tuples of ``(offset, length)`` 64-bit
unsigned native endian integers defining the byte offset and length of each
segment within the buffer.

Instances behave like containers.

``len()`` returns the number of segments within the instance.

``o[index]`` or ``__getitem__`` obtains a ``BufferSegment`` representing an
individual segment within the backing buffer. That returned object references
(not copies) memory. This means that iterating all objects doesn't copy
data within the buffer.

The ``.size`` attribute contains the total size in bytes of the backing
buffer.

Instances conform to the buffer protocol. So a reference to the backing bytes
can be obtained via ``memoryview(o)``. A *copy* of the backing bytes can also
be obtained via ``.tobytes()``.

The ``.segments`` attribute exposes the array of ``(offset, length)`` for
segments within the buffer. It is a ``BufferSegments`` type.

``BufferSegment``
=================

The ``BufferSegment`` type represents a segment within a ``BufferWithSegments``.
It is essentially a reference to N bytes within a ``BufferWithSegments``.

``len()`` returns the length of the segment in bytes.

``.offset`` contains the byte offset of this segment within its parent
``BufferWithSegments`` instance.

The object conforms to the buffer protocol. ``.tobytes()`` can be called to
obtain a ``bytes`` instance with a copy of the backing bytes.

``BufferSegments``
==================

This type represents an array of ``(offset, length)`` integers defining segments
within a ``BufferWithSegments``.

The array members are 64-bit unsigned integers using host/native bit order.

Instances conform to the buffer protocol.

``BufferWithSegmentsCollection``
================================

The ``BufferWithSegmentsCollection`` type represents a virtual spanning view
of multiple ``BufferWithSegments`` instances.

Instances are constructed from 1 or more ``BufferWithSegments`` instances. The
resulting object behaves like an ordered sequence whose members are the
segments within each ``BufferWithSegments``.

``len()`` returns the number of segments within all ``BufferWithSegments``
instances.

``o[index]`` and ``__getitem__(index)`` return the ``BufferSegment`` at
that offset as if all ``BufferWithSegments`` instances were a single
entity.

If the object is composed of 2 ``BufferWithSegments`` instances with the
first having 2 segments and the second have 3 segments, then ``b[0]``
and ``b[1]`` access segments in the first object and ``b[2]``, ``b[3]``,
and ``b[4]`` access segments from the second.
