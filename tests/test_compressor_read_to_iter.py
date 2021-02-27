import io
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
)


class TestCompressor_read_to_iter(unittest.TestCase):
    def test_type_validation(self):
        cctx = zstd.ZstdCompressor()

        # Object with read() works.
        for chunk in cctx.read_to_iter(io.BytesIO()):
            pass

        # Buffer protocol works.
        for chunk in cctx.read_to_iter(b"foobar"):
            pass

        with self.assertRaisesRegex(
            ValueError, "must pass an object with a read"
        ):
            for chunk in cctx.read_to_iter(True):
                pass

    def test_read_empty(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)

        source = io.BytesIO()
        it = cctx.read_to_iter(source)
        chunks = list(it)
        self.assertEqual(len(chunks), 1)
        compressed = b"".join(chunks)
        self.assertEqual(compressed, b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")

        # And again with the buffer protocol.
        it = cctx.read_to_iter(b"")
        chunks = list(it)
        self.assertEqual(len(chunks), 1)
        compressed2 = b"".join(chunks)
        self.assertEqual(compressed2, compressed)

    def test_read_large(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)

        source = io.BytesIO()
        source.write(b"f" * zstd.COMPRESSION_RECOMMENDED_INPUT_SIZE)
        source.write(b"o")
        source.seek(0)

        # Creating an iterator should not perform any compression until
        # first read.
        it = cctx.read_to_iter(source, size=len(source.getvalue()))
        self.assertEqual(source.tell(), 0)

        # We should have exactly 2 output chunks.
        chunks = []
        chunk = next(it)
        self.assertIsNotNone(chunk)
        self.assertEqual(source.tell(), zstd.COMPRESSION_RECOMMENDED_INPUT_SIZE)
        chunks.append(chunk)
        chunk = next(it)
        self.assertIsNotNone(chunk)
        chunks.append(chunk)

        self.assertEqual(source.tell(), len(source.getvalue()))

        with self.assertRaises(StopIteration):
            next(it)

        # And again for good measure.
        with self.assertRaises(StopIteration):
            next(it)

        # We should get the same output as the one-shot compression mechanism.
        self.assertEqual(b"".join(chunks), cctx.compress(source.getvalue()))

        params = zstd.get_frame_parameters(b"".join(chunks))
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Now check the buffer protocol.
        it = cctx.read_to_iter(source.getvalue())
        chunks = list(it)
        self.assertEqual(len(chunks), 2)

        params = zstd.get_frame_parameters(b"".join(chunks))
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        # self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        self.assertEqual(b"".join(chunks), cctx.compress(source.getvalue()))

    def test_read_write_size(self):
        source = CustomBytesIO(b"foobarfoobar")
        cctx = zstd.ZstdCompressor(level=3)
        for chunk in cctx.read_to_iter(source, read_size=1, write_size=1):
            self.assertEqual(len(chunk), 1)

        self.assertEqual(source._read_count, len(source.getvalue()) + 1)

    def test_multithreaded(self):
        source = io.BytesIO()
        source.write(b"a" * 1048576)
        source.write(b"b" * 1048576)
        source.write(b"c" * 1048576)
        source.seek(0)

        cctx = zstd.ZstdCompressor(threads=2)

        compressed = b"".join(cctx.read_to_iter(source))
        self.assertEqual(len(compressed), 111)

    def test_bad_size(self):
        cctx = zstd.ZstdCompressor()

        source = io.BytesIO(b"a" * 42)

        with self.assertRaisesRegex(zstd.ZstdError, "Src size is incorrect"):
            b"".join(cctx.read_to_iter(source, size=2))

        # Test another operation on errored compressor.
        b"".join(cctx.read_to_iter(source))

    def test_read_exception(self):
        b = CustomBytesIO(b"foo" * 1024)
        b.read_exception = IOError("read")

        cctx = zstd.ZstdCompressor()

        it = cctx.read_to_iter(b)

        with self.assertRaisesRegex(IOError, "read"):
            next(it)
