.. _api_usage:

=========
API Usage
=========

To interface with Zstandard, simply import the ``zstandard`` module:

.. code-block:: python

   import zstandard

It is a popular convention to alias the module as a different name for
brevity:

.. code-block:: python

   import zstandard as zstd

This module attempts to import and use either the C extension or CFFI
implementation. On Python platforms known to support C extensions (like
CPython), it raises an ImportError if the C extension cannot be imported.
On Python platforms known to not support C extensions (like PyPy), it only
attempts to import the CFFI implementation and raises ImportError if that
can't be done. On other platforms, it first tries to import the C extension
then falls back to CFFI if that fails and raises ImportError if CFFI fails.

To change the module import behavior, a ``PYTHON_ZSTANDARD_IMPORT_POLICY``
environment variable can be set. The following values are accepted:

``default``
   The behavior described above.
``cffi_fallback``
   Always try to import the C extension then fall back to CFFI if that
   fails.
``cext``
   Only attempt to import the C extension.
``cffi``
   Only attempt to import the CFFI implementation.

In addition, the ``zstandard`` module exports a ``backend`` attribute
containing the string name of the backend being used. It will be one
of ``cext`` or ``cffi`` (for *C extension* and *cffi*, respectively).

.. note::

   The documentation in this section makes references to various zstd
   concepts and functionality. See :ref:`concepts` for more details.

Choosing an API
===============

There are multiple APIs for performing compression and decompression. This is
because different applications have different needs and this library wants to
facilitate optimal use in as many use cases as possible.

From a high-level, APIs are divided into *one-shot* and *streaming*: either you
are operating on all data at once or you operate on it piecemeal.

The *one-shot* APIs are useful for small data, where the input or output
size is known. (The size can come from a buffer length, file size, or
stored in the zstd frame header.) A limitation of the *one-shot* APIs is that
input and output must fit in memory simultaneously. For say a 4 GB input,
this is often not feasible.

The *one-shot* APIs also perform all work as a single operation. So, if you
feed it large input, it could take a long time for the function to return.

The streaming APIs do not have the limitations of the simple API. But the
price you pay for this flexibility is that they are more complex than a
single function call.

The streaming APIs put the caller in control of compression and decompression
behavior by allowing them to directly control either the input or output side
of the operation.

With the *streaming input*, *compressor*, and *decompressor* APIs, the caller
has full control over the input to the compression or decompression stream.
They can directly choose when new data is operated on.

With the *streaming ouput* APIs, the caller has full control over the output
of the compression or decompression stream. It can choose when to receive
new data.

When using the *streaming* APIs that operate on file-like or stream objects,
it is important to consider what happens in that object when I/O is requested.
There is potential for long pauses as data is read or written from the
underlying stream (say from interacting with a filesystem or network). This
could add considerable overhead.

Thread and Object Reuse Safety
==============================

Unless stated otherwise, ``ZstdCompressor`` and ``ZstdDecompressor`` instances
cannot be used for temporally overlapping (de)compression operations. i.e.
if you start a (de)compression operation on an instance or a helper object
derived from it, it isn't safe to start another (de)compression operation
from the same instance until the first one has finished.

``ZstdCompressor`` and ``ZstdDecompressor`` instances have no guarantees
about thread safety. Do not operate on the same ``ZstdCompressor`` and
``ZstdDecompressor`` instance simultaneously from different threads. It is
fine to have different threads call into a single instance, just not at the
same time.

Objects derived from ``ZstdCompressor`` and ``ZstdDecompressor`` that
perform (de)compression operations (such as ``ZstdCompressionReader`` and
``ZstdDecompressionWriter``) are bound to the ``ZstdCompressor`` or
``ZstdDecompressor`` from which they came and are therefore not thread safe
by extension.

Some operations require multiple function calls to complete. e.g. streaming
operations. A single ``ZstdCompressor`` or ``ZstdDecompressor`` cannot be used
for simultaneously active operations. e.g. you must not start a streaming
operation when another streaming operation is already active.

If you need to perform multiple compression or decompression operations in
parallel, you MUST construct multiple ``ZstdCompressor`` or ``ZstdDecompressor``
instances so each independent operation has its own ``ZstdCompressor`` or
``ZstdDecompressor`` instance.

The C extension releases the GIL during non-trivial calls into the zstd C
API. Non-trivial calls are notably compression and decompression. Trivial
calls are things like parsing frame parameters. Where the GIL is released
is considered an implementation detail and can change in any release.

APIs that accept bytes-like objects don't enforce that the underlying object
is read-only. However, it is assumed that the passed object is read-only for
the duration of the function call. It is possible to pass a mutable object
(like a ``bytearray``) to e.g. ``ZstdCompressor.compress()``, have the GIL
released, and mutate the object from another thread. Such a race condition
is a bug in the consumer of python-zstandard. Most Python data types are
immutable, so unless you are doing something fancy, you don't need to
worry about this.

Performance Considerations
==========================

The ``ZstdCompressor`` and ``ZstdDecompressor`` types maintain state to a
persistent compression or decompression *context*. Reusing a ``ZstdCompressor``
or ``ZstdDecompressor`` instance for multiple operations is faster than
instantiating a new ``ZstdCompressor`` or ``ZstdDecompressor`` for each
operation. The differences are magnified as the size of data decreases. For
example, the difference between *context* reuse and non-reuse for 100,000
100 byte inputs will be significant (possibly over 10x faster to reuse contexts)
whereas 10 100,000,000 byte inputs will be more similar in speed (because the
time spent doing compression dwarfs time spent creating new *contexts*).


