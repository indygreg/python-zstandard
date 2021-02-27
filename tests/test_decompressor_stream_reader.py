import io
import os
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
)


class TestDecompressor_stream_reader(unittest.TestCase):
    def test_context_manager(self):
        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(b"foo") as reader:
            with self.assertRaisesRegex(
                ValueError, "cannot __enter__ multiple times"
            ):
                with reader as reader2:
                    pass

    def test_not_implemented(self):
        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(b"foo") as reader:
            with self.assertRaises(io.UnsupportedOperation):
                reader.readline()

            with self.assertRaises(io.UnsupportedOperation):
                reader.readlines()

            with self.assertRaises(io.UnsupportedOperation):
                iter(reader)

            with self.assertRaises(io.UnsupportedOperation):
                next(reader)

            with self.assertRaises(io.UnsupportedOperation):
                reader.write(b"foo")

            with self.assertRaises(io.UnsupportedOperation):
                reader.writelines([])

    def test_constant_methods(self):
        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(b"foo") as reader:
            self.assertFalse(reader.closed)
            self.assertTrue(reader.readable())
            self.assertFalse(reader.writable())
            self.assertFalse(reader.seekable())
            self.assertFalse(reader.isatty())
            self.assertFalse(reader.closed)
            self.assertIsNone(reader.flush())
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_read_closed(self):
        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(b"foo") as reader:
            reader.close()
            self.assertTrue(reader.closed)
            with self.assertRaisesRegex(ValueError, "stream is closed"):
                reader.read(1)

    def test_read_sizes(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(foo) as reader:
            with self.assertRaisesRegex(
                ValueError, "cannot read negative amounts less than -1"
            ):
                reader.read(-2)

            self.assertEqual(reader.read(0), b"")
            self.assertEqual(reader.read(), b"foo")

    def test_read_buffer(self):
        cctx = zstd.ZstdCompressor()

        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(frame) as reader:
            self.assertEqual(reader.tell(), 0)

            # We should get entire frame in one read.
            result = reader.read(8192)
            self.assertEqual(result, source)
            self.assertEqual(reader.tell(), len(source))

            # Read after EOF should return empty bytes.
            self.assertEqual(reader.read(1), b"")
            self.assertEqual(reader.tell(), len(result))

        self.assertTrue(reader.closed)

    def test_read_buffer_small_chunks(self):
        cctx = zstd.ZstdCompressor()
        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        chunks = []

        with dctx.stream_reader(frame, read_size=1) as reader:
            while True:
                chunk = reader.read(1)
                if not chunk:
                    break

                chunks.append(chunk)
                self.assertEqual(reader.tell(), sum(map(len, chunks)))

        self.assertEqual(b"".join(chunks), source)

    def test_read_stream(self):
        cctx = zstd.ZstdCompressor()
        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(io.BytesIO(frame)) as reader:
            self.assertEqual(reader.tell(), 0)

            chunk = reader.read(8192)
            self.assertEqual(chunk, source)
            self.assertEqual(reader.tell(), len(source))
            self.assertEqual(reader.read(1), b"")
            self.assertEqual(reader.tell(), len(source))
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_read_stream_small_chunks(self):
        cctx = zstd.ZstdCompressor()
        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        chunks = []

        with dctx.stream_reader(io.BytesIO(frame), read_size=1) as reader:
            while True:
                chunk = reader.read(1)
                if not chunk:
                    break

                chunks.append(chunk)
                self.assertEqual(reader.tell(), sum(map(len, chunks)))

        self.assertEqual(b"".join(chunks), source)

    def test_close(self):
        foo = zstd.ZstdCompressor().compress(b"foo" * 1024)

        buffer = io.BytesIO(foo)
        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(buffer)

        reader.read(3)
        self.assertFalse(reader.closed)
        self.assertFalse(buffer.closed)
        reader.close()
        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read()

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with reader:
                pass

        # Context manager exit should not close stream.
        buffer = io.BytesIO(foo)
        reader = dctx.stream_reader(buffer)

        with reader:
            reader.read(3)

        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        # Context manager exit should close stream if an exception raised.
        buffer = io.BytesIO(foo)
        reader = dctx.stream_reader(buffer)

        with self.assertRaisesRegex(Exception, "ignore"):
            with reader:
                reader.read(3)
                raise Exception("ignore")

        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        # Test with non-file source variant.
        with dctx.stream_reader(foo) as reader:
            reader.read(3)
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_close_closefd_false(self):
        foo = zstd.ZstdCompressor().compress(b"foo" * 1024)

        buffer = io.BytesIO(foo)
        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(buffer, closefd=False)

        reader.read(3)
        self.assertFalse(reader.closed)
        self.assertFalse(buffer.closed)
        reader.close()
        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read()

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with reader:
                pass

        # Context manager exit should not close stream.
        buffer = io.BytesIO(foo)
        reader = dctx.stream_reader(buffer, closefd=False)

        with reader:
            reader.read(3)

        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        # Context manager exit should close stream if an exception raised.
        buffer = io.BytesIO(foo)
        reader = dctx.stream_reader(buffer, closefd=False)

        with self.assertRaisesRegex(Exception, "ignore"):
            with reader:
                reader.read(3)
                raise Exception("ignore")

        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        # Test with non-file source variant.
        with dctx.stream_reader(foo, closefd=False) as reader:
            reader.read(3)
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_read_after_exit(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"foo" * 60)

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(frame) as reader:
            while reader.read(16):
                pass

        self.assertTrue(reader.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(10)

    def test_illegal_seeks(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"foo" * 60)

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(frame) as reader:
            with self.assertRaisesRegex(
                OSError, "cannot seek to negative position"
            ):
                reader.seek(-1, os.SEEK_SET)

            reader.read(1)

            with self.assertRaisesRegex(
                OSError, "cannot seek zstd decompression stream backwards"
            ):
                reader.seek(0, os.SEEK_SET)

            with self.assertRaisesRegex(
                OSError, "cannot seek zstd decompression stream backwards"
            ):
                reader.seek(-1, os.SEEK_CUR)

            with self.assertRaisesRegex(
                OSError,
                "zstd decompression streams cannot be seeked with SEEK_END",
            ):
                reader.seek(0, os.SEEK_END)

            reader.close()

            with self.assertRaisesRegex(ValueError, "stream is closed"):
                reader.seek(4, os.SEEK_SET)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.seek(0)

    def test_seek(self):
        source = b"foobar" * 60
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(frame) as reader:
            reader.seek(3)
            self.assertEqual(reader.read(3), b"bar")

            reader.seek(4, os.SEEK_CUR)
            self.assertEqual(reader.read(2), b"ar")

    def test_no_context_manager(self):
        source = b"foobar" * 60
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(frame)

        self.assertEqual(reader.read(6), b"foobar")
        self.assertEqual(reader.read(18), b"foobar" * 3)
        self.assertFalse(reader.closed)

        # Calling close prevents subsequent use.
        reader.close()
        self.assertTrue(reader.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(6)

    def test_read_after_error(self):
        source = io.BytesIO(b"")
        dctx = zstd.ZstdDecompressor()

        reader = dctx.stream_reader(source)

        with reader:
            reader.read(0)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with reader:
                pass

    def test_partial_read(self):
        # Inspired by https://github.com/indygreg/python-zstandard/issues/71.
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        writer = cctx.stream_writer(buffer)
        writer.write(bytearray(os.urandom(1000000)))
        writer.flush(zstd.FLUSH_FRAME)
        buffer.seek(0)

        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(buffer)

        while True:
            chunk = reader.read(8192)
            if not chunk:
                break

    def test_read_multiple_frames(self):
        cctx = zstd.ZstdCompressor()
        source = io.BytesIO()
        writer = cctx.stream_writer(source)
        writer.write(b"foo")
        writer.flush(zstd.FLUSH_FRAME)
        writer.write(b"bar")
        writer.flush(zstd.FLUSH_FRAME)

        dctx = zstd.ZstdDecompressor()

        reader = dctx.stream_reader(source.getvalue())
        self.assertEqual(reader.read(2), b"fo")
        self.assertEqual(reader.read(2), b"o")
        self.assertEqual(reader.read(2), b"ba")
        self.assertEqual(reader.read(2), b"r")

        source.seek(0)
        reader = dctx.stream_reader(source)
        self.assertEqual(reader.read(2), b"fo")
        self.assertEqual(reader.read(2), b"o")
        self.assertEqual(reader.read(2), b"ba")
        self.assertEqual(reader.read(2), b"r")

        reader = dctx.stream_reader(source.getvalue())
        self.assertEqual(reader.read(3), b"foo")
        self.assertEqual(reader.read(3), b"bar")

        source.seek(0)
        reader = dctx.stream_reader(source)
        self.assertEqual(reader.read(3), b"foo")
        self.assertEqual(reader.read(3), b"bar")

        reader = dctx.stream_reader(source.getvalue())
        self.assertEqual(reader.read(4), b"foo")
        self.assertEqual(reader.read(4), b"bar")

        source.seek(0)
        reader = dctx.stream_reader(source)
        self.assertEqual(reader.read(4), b"foo")
        self.assertEqual(reader.read(4), b"bar")

        reader = dctx.stream_reader(source.getvalue())
        self.assertEqual(reader.read(128), b"foo")
        self.assertEqual(reader.read(128), b"bar")

        source.seek(0)
        reader = dctx.stream_reader(source)
        self.assertEqual(reader.read(128), b"foo")
        self.assertEqual(reader.read(128), b"bar")

        # Now tests for reads spanning frames.
        reader = dctx.stream_reader(source.getvalue(), read_across_frames=True)
        self.assertEqual(reader.read(3), b"foo")
        self.assertEqual(reader.read(3), b"bar")

        source.seek(0)
        reader = dctx.stream_reader(source, read_across_frames=True)
        self.assertEqual(reader.read(3), b"foo")
        self.assertEqual(reader.read(3), b"bar")

        reader = dctx.stream_reader(source.getvalue(), read_across_frames=True)
        self.assertEqual(reader.read(6), b"foobar")

        source.seek(0)
        reader = dctx.stream_reader(source, read_across_frames=True)
        self.assertEqual(reader.read(6), b"foobar")

        reader = dctx.stream_reader(source.getvalue(), read_across_frames=True)
        self.assertEqual(reader.read(7), b"foobar")

        source.seek(0)
        reader = dctx.stream_reader(source, read_across_frames=True)
        self.assertEqual(reader.read(7), b"foobar")

        reader = dctx.stream_reader(source.getvalue(), read_across_frames=True)
        self.assertEqual(reader.read(128), b"foobar")

        source.seek(0)
        reader = dctx.stream_reader(source, read_across_frames=True)
        self.assertEqual(reader.read(128), b"foobar")

    def test_readinto(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        dctx = zstd.ZstdDecompressor()

        # Attempting to readinto() a non-writable buffer fails.
        # The exact exception varies based on the backend.
        reader = dctx.stream_reader(foo)
        with self.assertRaises(Exception):
            reader.readinto(b"foobar")

        # readinto() with sufficiently large destination.
        b = bytearray(1024)
        reader = dctx.stream_reader(foo)
        self.assertEqual(reader.readinto(b), 3)
        self.assertEqual(b[0:3], b"foo")
        self.assertEqual(reader.readinto(b), 0)
        self.assertEqual(b[0:3], b"foo")

        # readinto() with small reads.
        b = bytearray(1024)
        reader = dctx.stream_reader(foo, read_size=1)
        self.assertEqual(reader.readinto(b), 3)
        self.assertEqual(b[0:3], b"foo")

        # Too small destination buffer.
        b = bytearray(2)
        reader = dctx.stream_reader(foo)
        self.assertEqual(reader.readinto(b), 2)
        self.assertEqual(b[:], b"fo")

    def test_readinto1(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        dctx = zstd.ZstdDecompressor()

        reader = dctx.stream_reader(foo)
        with self.assertRaises(Exception):
            reader.readinto1(b"foobar")

        # Sufficiently large destination.
        b = bytearray(1024)
        reader = dctx.stream_reader(foo)
        self.assertEqual(reader.readinto1(b), 3)
        self.assertEqual(b[0:3], b"foo")
        self.assertEqual(reader.readinto1(b), 0)
        self.assertEqual(b[0:3], b"foo")

        # readinto() with small reads.
        b = bytearray(1024)
        reader = dctx.stream_reader(foo, read_size=1)
        self.assertEqual(reader.readinto1(b), 3)
        self.assertEqual(b[0:3], b"foo")

        # Too small destination buffer.
        b = bytearray(2)
        reader = dctx.stream_reader(foo)
        self.assertEqual(reader.readinto1(b), 2)
        self.assertEqual(b[:], b"fo")

    def test_readall(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(foo)

        self.assertEqual(reader.readall(), b"foo")

    def test_read1(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        dctx = zstd.ZstdDecompressor()

        b = CustomBytesIO(foo)
        reader = dctx.stream_reader(b)

        self.assertEqual(reader.read1(), b"foo")
        self.assertEqual(b._read_count, 1)

        b = CustomBytesIO(foo)
        reader = dctx.stream_reader(b)

        self.assertEqual(reader.read1(0), b"")
        self.assertEqual(reader.read1(2), b"fo")
        self.assertEqual(b._read_count, 1)
        self.assertEqual(reader.read1(1), b"o")
        self.assertEqual(b._read_count, 1)
        self.assertEqual(reader.read1(1), b"")
        self.assertEqual(b._read_count, 2)

    def test_read_lines(self):
        cctx = zstd.ZstdCompressor()
        source = b"\n".join(
            ("line %d" % i).encode("ascii") for i in range(1024)
        )

        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(frame)
        tr = io.TextIOWrapper(reader, encoding="utf-8")

        lines = []
        for line in tr:
            lines.append(line.encode("utf-8"))

        self.assertEqual(len(lines), 1024)
        self.assertEqual(b"".join(lines), source)

        reader = dctx.stream_reader(frame)
        tr = io.TextIOWrapper(reader, encoding="utf-8")

        lines = tr.readlines()
        self.assertEqual(len(lines), 1024)
        self.assertEqual("".join(lines).encode("utf-8"), source)

        reader = dctx.stream_reader(frame)
        tr = io.TextIOWrapper(reader, encoding="utf-8")

        lines = []
        while True:
            line = tr.readline()
            if not line:
                break

            lines.append(line.encode("utf-8"))

        self.assertEqual(len(lines), 1024)
        self.assertEqual(b"".join(lines), source)
