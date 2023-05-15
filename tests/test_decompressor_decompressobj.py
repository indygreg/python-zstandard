import unittest

import zstandard as zstd


class TestDecompressor_decompressobj(unittest.TestCase):
    def test_simple(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        self.assertEqual(dobj.unused_data, b"")
        self.assertEqual(dobj.unconsumed_tail, b"")
        self.assertFalse(dobj.eof)
        self.assertEqual(dobj.decompress(data), b"foobar")
        self.assertEqual(dobj.unused_data, b"")
        self.assertEqual(dobj.unconsumed_tail, b"")
        self.assertTrue(dobj.eof)
        self.assertEqual(dobj.flush(), b"")
        self.assertEqual(dobj.flush(10), b"")
        self.assertEqual(dobj.flush(length=100), b"")
        self.assertEqual(dobj.unused_data, b"")
        self.assertEqual(dobj.unconsumed_tail, b"")

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
            self.assertEqual(dobj.unused_data, b"")
            self.assertEqual(dobj.unconsumed_tail, b"")
            self.assertFalse(dobj.eof)
            self.assertEqual(dobj.flush(), b"")
            self.assertEqual(dobj.flush(10), b"")
            self.assertEqual(dobj.flush(length=100), b"")
            self.assertEqual(dobj.decompress(source), b"foo")
            self.assertEqual(dobj.unused_data, b"")
            self.assertEqual(dobj.unconsumed_tail, b"")
            self.assertTrue(dobj.eof)
            self.assertEqual(dobj.flush(), b"")

    def test_unused_data(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        self.assertEqual(dobj.unused_data, b"")
        self.assertEqual(dobj.decompress(data + b"extra"), b"foobar")
        self.assertTrue(dobj.eof)
        self.assertEqual(dobj.unused_data, b"extra")

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

    def test_multiple_decompress_calls(self):
        expected = b"foobar" * 10
        data = zstd.ZstdCompressor(level=1).compress(expected)

        N = 3
        partitioned_data = [
            data[len(data) * i // N : len(data) * (i + 1) // N]
            for i in range(N)
        ]

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()

        for partition in partitioned_data[:-1]:
            decompressed = dobj.decompress(partition)
            self.assertEqual(decompressed, b"")
            self.assertEqual(dobj.unused_data, b"")

        decompressed = dobj.decompress(partitioned_data[-1])
        self.assertEqual(decompressed, expected)

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

    def test_multiple_frames_default(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")
        bar = cctx.compress(b"bar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()

        self.assertEqual(dobj.decompress(foo + bar), b"foo")
        self.assertEqual(dobj.unused_data, bar)
        self.assertEqual(dobj.unconsumed_tail, b"")

    def test_read_across_frames_false(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")
        bar = cctx.compress(b"bar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj(read_across_frames=False)

        self.assertEqual(dobj.decompress(foo + bar), b"foo")
        self.assertEqual(dobj.unused_data, bar)
        self.assertEqual(dobj.unconsumed_tail, b"")

    def test_read_across_frames_true(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")
        bar = cctx.compress(b"bar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj(read_across_frames=True)

        self.assertEqual(dobj.decompress(foo + bar), b"foobar")
        self.assertEqual(dobj.unused_data, b"")
        self.assertEqual(dobj.unconsumed_tail, b"")
