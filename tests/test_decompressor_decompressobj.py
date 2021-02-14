import unittest

import zstandard as zstd


class TestDecompressor_decompressobj(unittest.TestCase):
    def test_simple(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        self.assertEqual(dobj.decompress(data), b"foobar")
        self.assertEqual(dobj.flush(), b"")
        self.assertEqual(dobj.flush(10), b"")
        self.assertEqual(dobj.flush(length=100), b"")

    def test_input_types(self):
        compressed = zstd.ZstdCompressor(level=1).compress(b"foo")

        dctx = zstd.ZstdDecompressor()

        mutable_array = bytearray(len(compressed))
        mutable_array[:] = compressed

        sources = [
            memoryview(compressed),
            bytearray(compressed),
            mutable_array,
        ]

        for source in sources:
            dobj = dctx.decompressobj()
            self.assertEqual(dobj.flush(), b"")
            self.assertEqual(dobj.flush(10), b"")
            self.assertEqual(dobj.flush(length=100), b"")
            self.assertEqual(dobj.decompress(source), b"foo")
            self.assertEqual(dobj.flush(), b"")

    def test_reuse(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        dobj.decompress(data)

        with self.assertRaisesRegex(
            zstd.ZstdError, "cannot use a decompressobj"
        ):
            dobj.decompress(data)
            self.assertEqual(dobj.flush(), b"")

    def test_bad_write_size(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(ValueError, "write_size must be positive"):
            dctx.decompressobj(write_size=0)

    def test_write_size(self):
        source = b"foo" * 64 + b"bar" * 128
        data = zstd.ZstdCompressor(level=1).compress(source)

        dctx = zstd.ZstdDecompressor()

        for i in range(128):
            dobj = dctx.decompressobj(write_size=i + 1)
            self.assertEqual(dobj.decompress(data), source)
