import io
import struct
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
)


class TestCompressor_copy_stream(unittest.TestCase):
    def test_no_read(self):
        source = object()
        dest = io.BytesIO()

        cctx = zstd.ZstdCompressor()
        with self.assertRaises(ValueError):
            cctx.copy_stream(source, dest)

    def test_no_write(self):
        source = io.BytesIO()
        dest = object()

        cctx = zstd.ZstdCompressor()
        with self.assertRaises(ValueError):
            cctx.copy_stream(source, dest)

    def test_empty(self):
        source = io.BytesIO()
        dest = io.BytesIO()

        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        r, w = cctx.copy_stream(source, dest)
        self.assertEqual(int(r), 0)
        self.assertEqual(w, 9)

        self.assertEqual(
            dest.getvalue(), b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00"
        )

    def test_large_data(self):
        source = io.BytesIO()
        for i in range(255):
            source.write(struct.Struct(">B").pack(i) * 16384)
        source.seek(0)

        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        r, w = cctx.copy_stream(source, dest)

        self.assertEqual(r, 255 * 16384)
        self.assertEqual(w, 999)

        params = zstd.get_frame_parameters(dest.getvalue())
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 2097152)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

    def test_write_checksum(self):
        source = io.BytesIO(b"foobar")
        no_checksum = io.BytesIO()

        cctx = zstd.ZstdCompressor(level=1)
        cctx.copy_stream(source, no_checksum)

        source.seek(0)
        with_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        cctx.copy_stream(source, with_checksum)

        self.assertEqual(
            len(with_checksum.getvalue()), len(no_checksum.getvalue()) + 4
        )

        no_params = zstd.get_frame_parameters(no_checksum.getvalue())
        with_params = zstd.get_frame_parameters(with_checksum.getvalue())
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertTrue(with_params.has_checksum)

    def test_write_content_size(self):
        source = io.BytesIO(b"foobar" * 256)
        no_size = io.BytesIO()

        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        cctx.copy_stream(source, no_size)

        source.seek(0)
        with_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        cctx.copy_stream(source, with_size)

        # Source content size is unknown, so no content size written.
        self.assertEqual(len(with_size.getvalue()), len(no_size.getvalue()))

        source.seek(0)
        with_size = io.BytesIO()
        cctx.copy_stream(source, with_size, size=len(source.getvalue()))

        # We specified source size, so content size header is present.
        self.assertEqual(len(with_size.getvalue()), len(no_size.getvalue()) + 1)

        no_params = zstd.get_frame_parameters(no_size.getvalue())
        with_params = zstd.get_frame_parameters(with_size.getvalue())
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, 1536)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertFalse(with_params.has_checksum)

    def test_read_write_size(self):
        source = CustomBytesIO(b"foobarfoobar")
        dest = CustomBytesIO()
        cctx = zstd.ZstdCompressor()
        r, w = cctx.copy_stream(source, dest, read_size=1, write_size=1)

        self.assertEqual(r, len(source.getvalue()))
        self.assertEqual(w, 21)
        self.assertEqual(source._read_count, len(source.getvalue()) + 1)
        self.assertEqual(dest._write_count, len(dest.getvalue()))

    def test_multithreaded(self):
        source = io.BytesIO()
        source.write(b"a" * 1048576)
        source.write(b"b" * 1048576)
        source.write(b"c" * 1048576)
        source.seek(0)

        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor(threads=2, write_content_size=False)
        r, w = cctx.copy_stream(source, dest)
        self.assertEqual(r, 3145728)
        self.assertEqual(w, 111)

        params = zstd.get_frame_parameters(dest.getvalue())
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Writing content size and checksum works.
        cctx = zstd.ZstdCompressor(threads=2, write_checksum=True)
        dest = io.BytesIO()
        source.seek(0)
        cctx.copy_stream(source, dest, size=len(source.getvalue()))

        params = zstd.get_frame_parameters(dest.getvalue())
        self.assertEqual(params.content_size, 3145728)
        self.assertEqual(params.dict_id, 0)
        self.assertTrue(params.has_checksum)

    def test_bad_size(self):
        source = io.BytesIO()
        source.write(b"a" * 32768)
        source.write(b"b" * 32768)
        source.seek(0)

        dest = io.BytesIO()

        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(zstd.ZstdError, "Src size is incorrect"):
            cctx.copy_stream(source, dest, size=42)

        # Try another operation on this compressor.
        source.seek(0)
        dest = io.BytesIO()
        cctx.copy_stream(source, dest)

    def test_read_exception(self):
        source = CustomBytesIO(b"foo" * 1024)
        dest = CustomBytesIO()

        source.read_exception = IOError("read")

        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(IOError, "read"):
            cctx.copy_stream(source, dest)

    def test_write_exception(self):
        source = CustomBytesIO(b"foo" * 1024)
        dest = CustomBytesIO()

        dest.write_exception = IOError("write")

        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(IOError, "write"):
            cctx.copy_stream(source, dest)
