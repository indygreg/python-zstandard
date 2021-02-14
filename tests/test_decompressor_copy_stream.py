import io
import struct
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
)


class TestDecompressor_copy_stream(unittest.TestCase):
    def test_no_read(self):
        source = object()
        dest = io.BytesIO()

        dctx = zstd.ZstdDecompressor()
        with self.assertRaises(ValueError):
            dctx.copy_stream(source, dest)

    def test_no_write(self):
        source = io.BytesIO()
        dest = object()

        dctx = zstd.ZstdDecompressor()
        with self.assertRaises(ValueError):
            dctx.copy_stream(source, dest)

    def test_empty(self):
        source = io.BytesIO()
        dest = io.BytesIO()

        dctx = zstd.ZstdDecompressor()
        # TODO should this raise an error?
        r, w = dctx.copy_stream(source, dest)

        self.assertEqual(r, 0)
        self.assertEqual(w, 0)
        self.assertEqual(dest.getvalue(), b"")

    def test_large_data(self):
        source = io.BytesIO()
        for i in range(255):
            source.write(struct.Struct(">B").pack(i) * 16384)
        source.seek(0)

        compressed = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        cctx.copy_stream(source, compressed)

        compressed.seek(0)
        dest = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        r, w = dctx.copy_stream(compressed, dest)

        self.assertEqual(r, len(compressed.getvalue()))
        self.assertEqual(w, len(source.getvalue()))

    def test_read_write_size(self):
        source = CustomBytesIO(zstd.ZstdCompressor().compress(b"foobarfoobar"))

        dest = CustomBytesIO()
        dctx = zstd.ZstdDecompressor()
        r, w = dctx.copy_stream(source, dest, read_size=1, write_size=1)

        self.assertEqual(r, len(source.getvalue()))
        self.assertEqual(w, len(b"foobarfoobar"))
        self.assertEqual(source._read_count, len(source.getvalue()) + 1)
        self.assertEqual(dest._write_count, len(dest.getvalue()))

    def test_read_exception(self):
        source = CustomBytesIO(zstd.ZstdCompressor().compress(b"foo" * 1024))
        dest = CustomBytesIO()

        source.read_exception = IOError("read")

        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(IOError, "read"):
            cctx.copy_stream(source, dest)

    def test_write_exception(self):
        source = CustomBytesIO(zstd.ZstdCompressor().compress(b"foo" * 1024))
        dest = CustomBytesIO()

        dest.write_exception = IOError("write")

        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(IOError, "write"):
            cctx.copy_stream(source, dest)
