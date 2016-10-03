History of the Project
======================

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
