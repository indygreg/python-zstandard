import io
import os
import struct
import tempfile
import unittest

import zstandard as zstd

from .common import (
    NonClosingBytesIO,
    CustomBytesIO,
)


def decompress_via_writer(data):
    buffer = io.BytesIO()
    dctx = zstd.ZstdDecompressor()
    decompressor = dctx.stream_writer(buffer)
    decompressor.write(data)

    return buffer.getvalue()


class TestDecompressor_stream_writer(unittest.TestCase):
    def test_io_api(self):
        buffer = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        writer = dctx.stream_writer(buffer)

        self.assertFalse(writer.closed)
        self.assertFalse(writer.isatty())
        self.assertFalse(writer.readable())

        with self.assertRaises(io.UnsupportedOperation):
            writer.__iter__()

        with self.assertRaises(io.UnsupportedOperation):
            writer.__next__()

        with self.assertRaises(io.UnsupportedOperation):
            writer.readline()

        with self.assertRaises(io.UnsupportedOperation):
            writer.readline(42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.readline(size=42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.readlines()

        with self.assertRaises(io.UnsupportedOperation):
            writer.readlines(42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.readlines(hint=42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.seek(0)

        with self.assertRaises(io.UnsupportedOperation):
            writer.seek(10, os.SEEK_SET)

        self.assertFalse(writer.seekable())

        with self.assertRaises(io.UnsupportedOperation):
            writer.tell()

        with self.assertRaises(io.UnsupportedOperation):
            writer.truncate()

        with self.assertRaises(io.UnsupportedOperation):
            writer.truncate(42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.truncate(size=42)

        self.assertTrue(writer.writable())

        with self.assertRaises(io.UnsupportedOperation):
            writer.writelines([])

        with self.assertRaises(io.UnsupportedOperation):
            writer.read()

        with self.assertRaises(io.UnsupportedOperation):
            writer.read(42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.read(size=42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.readall()

        with self.assertRaises(io.UnsupportedOperation):
            writer.readinto(None)

        with self.assertRaises(io.UnsupportedOperation):
            writer.fileno()

    def test_fileno_file(self):
        with tempfile.TemporaryFile("wb") as tf:
            dctx = zstd.ZstdDecompressor()
            writer = dctx.stream_writer(tf)

            self.assertEqual(writer.fileno(), tf.fileno())

    def test_close(self):
        foo = zstd.ZstdCompressor().compress(b"foo")

        buffer = NonClosingBytesIO()
        dctx = zstd.ZstdDecompressor()
        writer = dctx.stream_writer(buffer)

        writer.write(foo)
        self.assertFalse(writer.closed)
        self.assertFalse(buffer.closed)
        writer.close()
        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.write(b"")

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.flush()

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with writer:
                pass

        self.assertEqual(buffer.getvalue(), b"foo")

        # Context manager exit should close stream.
        buffer = CustomBytesIO()
        writer = dctx.stream_writer(buffer)

        with writer:
            writer.write(foo)

        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

        # Context manager exit should close stream if an exception raised.
        buffer = CustomBytesIO()
        writer = dctx.stream_writer(buffer)

        with self.assertRaisesRegex(Exception, "ignore"):
            with writer:
                writer.write(foo)
                raise Exception("ignore")

        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

    def test_close_closefd_false(self):
        foo = zstd.ZstdCompressor().compress(b"foo")

        buffer = NonClosingBytesIO()
        dctx = zstd.ZstdDecompressor()
        writer = dctx.stream_writer(buffer, closefd=False)

        writer.write(foo)
        self.assertFalse(writer.closed)
        self.assertFalse(buffer.closed)
        writer.close()
        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.write(b"")

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.flush()

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with writer:
                pass

        self.assertEqual(buffer.getvalue(), b"foo")

        # Context manager exit should close stream.
        buffer = CustomBytesIO()
        writer = dctx.stream_writer(buffer, closefd=False)

        with writer:
            writer.write(foo)

        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

        # Context manager exit should close stream if an exception raised.
        buffer = CustomBytesIO()
        writer = dctx.stream_writer(buffer, closefd=False)

        with self.assertRaisesRegex(Exception, "ignore"):
            with writer:
                writer.write(foo)
                raise Exception("ignore")

        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

    def test_flush(self):
        buffer = CustomBytesIO()
        dctx = zstd.ZstdDecompressor()
        writer = dctx.stream_writer(buffer)

        writer.flush()
        self.assertEqual(buffer._flush_count, 1)
        writer.flush()
        self.assertEqual(buffer._flush_count, 2)

    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor()
        empty = cctx.compress(b"")
        self.assertEqual(decompress_via_writer(empty), b"")

    def test_input_types(self):
        cctx = zstd.ZstdCompressor(level=1)
        compressed = cctx.compress(b"foo")

        mutable_array = bytearray(len(compressed))
        mutable_array[:] = compressed

        sources = [
            memoryview(compressed),
            bytearray(compressed),
            mutable_array,
        ]

        dctx = zstd.ZstdDecompressor()
        for source in sources:
            buffer = io.BytesIO()

            decompressor = dctx.stream_writer(buffer)
            decompressor.write(source)
            self.assertEqual(buffer.getvalue(), b"foo")

            buffer = io.BytesIO()

            with dctx.stream_writer(buffer, closefd=False) as decompressor:
                self.assertEqual(decompressor.write(source), len(source))

            self.assertEqual(buffer.getvalue(), b"foo")

            buffer = io.BytesIO()
            writer = dctx.stream_writer(buffer, write_return_read=False)
            self.assertEqual(writer.write(source), 3)
            self.assertEqual(buffer.getvalue(), b"foo")

    def test_large_roundtrip(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct(">B").pack(i) * 16384)
        orig = b"".join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        self.assertEqual(decompress_via_writer(compressed), orig)

    def test_multiple_calls(self):
        chunks = []
        for i in range(255):
            for j in range(255):
                chunks.append(struct.Struct(">B").pack(j) * i)

        orig = b"".join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        buffer = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_writer(buffer, closefd=False) as decompressor:
            pos = 0
            while pos < len(compressed):
                pos2 = pos + 8192
                decompressor.write(compressed[pos:pos2])
                pos += 8192
        self.assertEqual(buffer.getvalue(), orig)

        # Again with write_return_read=False
        buffer = io.BytesIO()
        writer = dctx.stream_writer(buffer, write_return_read=False)
        pos = 0
        buffer_len = len(buffer.getvalue())
        while pos < len(compressed):
            pos2 = pos + 8192
            chunk = compressed[pos:pos2]
            self.assertEqual(
                writer.write(chunk), len(buffer.getvalue()) - buffer_len
            )
            buffer_len = len(buffer.getvalue())
            pos += 8192
        self.assertEqual(buffer.getvalue(), orig)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        orig = b"foobar" * 16384
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(dict_data=d)
        with cctx.stream_writer(buffer, closefd=False) as compressor:
            self.assertEqual(compressor.write(orig), len(orig))

        compressed = buffer.getvalue()
        buffer = io.BytesIO()

        dctx = zstd.ZstdDecompressor(dict_data=d)
        decompressor = dctx.stream_writer(buffer)
        self.assertEqual(decompressor.write(compressed), len(compressed))
        self.assertEqual(buffer.getvalue(), orig)

        buffer = io.BytesIO()

        with dctx.stream_writer(buffer, closefd=False) as decompressor:
            self.assertEqual(decompressor.write(compressed), len(compressed))

        self.assertEqual(buffer.getvalue(), orig)

    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()
        buffer = io.BytesIO()

        decompressor = dctx.stream_writer(buffer)
        size = decompressor.memory_size()
        self.assertGreater(size, 90000)

        with dctx.stream_writer(buffer) as decompressor:
            size = decompressor.memory_size()

        self.assertGreater(size, 90000)

    def test_write_size(self):
        source = zstd.ZstdCompressor().compress(b"foobarfoobar")
        dest = CustomBytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_writer(
            dest, write_size=1, closefd=False
        ) as decompressor:
            s = struct.Struct(">B")
            for c in source:
                if not isinstance(c, str):
                    c = s.pack(c)
                decompressor.write(c)

        self.assertEqual(dest.getvalue(), b"foobarfoobar")
        self.assertEqual(dest._write_count, len(dest.getvalue()))

    def test_write_exception(self):
        frame = zstd.ZstdCompressor().compress(b"foo" * 1024)

        b = CustomBytesIO()
        b.write_exception = IOError("write")

        dctx = zstd.ZstdDecompressor()

        writer = dctx.stream_writer(b)

        with self.assertRaisesRegex(IOError, "write"):
            writer.write(frame)
