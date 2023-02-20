.. _concepts:

========
Concepts
========

It is useful to have a basic understanding of how Zstandard works in order
to optimally use this library. In addition, there are some low-level Python
concepts that are worth explaining to aid understanding. This article aims to
provide that knowledge.

Zstandard Frames and Compression Format
=======================================

Compressed zstandard data almost always exists within a container called a
*frame*. (For the technically curious, see the
`specification <https://github.com/facebook/zstd/blob/3bee41a70eaf343fbcae3637b3f6edbe52f35ed8/doc/zstd_compression_format.md>`_.)

The frame contains a header and optional trailer. The header contains a
magic number to self-identify as a zstd frame and a description of the
compressed data that follows.

Among other things, the frame *optionally* contains the size of the
decompressed data the frame represents, a 32-bit checksum of the
decompressed data (to facilitate verification during decompression),
and the ID of the dictionary used to compress the data.

Storing the original content size in the frame (``write_content_size=True``
to ``ZstdCompressor``) is important for performance in some scenarios. Having
the decompressed size stored there (or storing it elsewhere) allows
decompression to perform a single memory allocation that is exactly sized to
the output. This is faster than continuously growing a memory buffer to hold
output.

Compression and Decompression Contexts
======================================

In order to perform a compression or decompression operation with the zstd
C API, you need what's called a *context*. A context essentially holds
configuration and state for a compression or decompression operation. For
example, a compression context holds the configured compression level.

Contexts can be reused for multiple operations. Since creating and
destroying contexts is not free, there are performance advantages to
reusing contexts.

The ``ZstdCompressor`` and ``ZstdDecompressor`` types are essentially
wrappers around these contexts in the zstd C API.

One-shot And Streaming Operations
=================================

A compression or decompression operation can either be performed as a
single *one-shot* operation or as a continuous *streaming* operation.

In one-shot mode (the *simple* APIs provided by the Python interface),
**all** input is handed to the compressor or decompressor as a single buffer
and **all** output is returned as a single buffer.

In streaming mode, input is delivered to the compressor or decompressor as
a series of chunks via multiple function calls. Likewise, output is
obtained in chunks as well.

Streaming operations require an additional *stream* object to be created
to track the operation. These are logical extensions of *context*
instances.

There are advantages and disadvantages to each mode of operation. There
are scenarios where certain modes can't be used. See the
``Choosing an API`` section for more.

Dictionaries
============

A compression *dictionary* is essentially data used to seed the compressor
state so it can achieve better compression. The idea is that if you are
compressing a lot of similar pieces of data (e.g. JSON documents or anything
sharing similar structure), then you can find common patterns across multiple
objects then leverage those common patterns during compression and
decompression operations to achieve better compression ratios.

Dictionary compression is generally only useful for small inputs - data no
larger than a few kilobytes. The upper bound on this range is highly dependent
on the input data and the dictionary.

Python Buffer Protocol
======================

Many functions in the library operate on objects that implement Python's
`buffer protocol <https://docs.python.org/3.11/c-api/buffer.html>`_.

The *buffer protocol* is an internal implementation detail of a Python
type that allows instances of that type (objects) to be exposed as a raw
pointer (or buffer) in the C API. In other words, it allows objects to be
exposed as an array of bytes.

From the perspective of the C API, objects implementing the *buffer protocol*
all look the same: they are just a pointer to a memory address of a defined
length. This allows the C API to be largely type agnostic when accessing their
data. This allows custom types to be passed in without first converting them
to a specific type.

Many Python types implement the buffer protocol. These include ``bytes``,
``bytearray``, ``array.array``, ``io.BytesIO``, ``mmap.mmap``, and
``memoryview``.

Requiring Output Sizes for Non-Streaming Decompression APIs
===========================================================

Non-streaming decompression APIs require that either the output size is
explicitly defined (either in the zstd frame header or passed into the
function) or that a max output size is specified. This restriction is for
your safety.

The *one-shot* decompression APIs store the decompressed result in a
single buffer. This means that a buffer needs to be pre-allocated to hold
the result. If the decompressed size is not known, then there is no universal
good default size to use. Any default will fail or will be highly sub-optimal
in some scenarios (it will either be too small or will put stress on the
memory allocator to allocate a too large block).

A *helpful* API may retry decompression with buffers of increasing size.
While useful, there are obvious performance disadvantages, namely redoing
decompression N times until it works. In addition, there is a security
concern. Say the input came from highly compressible data, like 1 GB of the
same byte value. The output size could be several magnitudes larger than the
input size. An input of <100KB could decompress to >1GB. Without a bounds
restriction on the decompressed size, certain inputs could exhaust all system
memory. That's not good and is why the maximum output size is limited.
