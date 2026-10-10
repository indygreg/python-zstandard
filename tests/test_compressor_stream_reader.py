import io
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
    NonClosingBytesIO,
)


class TestCompressor_stream_reader(unittest.TestCase):
    def test_context_manager(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"foo") as reader:
            with self.assertRaisesRegex(
                ValueError, "cannot __enter__ multiple times"
            ):
                with reader:
                    pass

    def test_no_context_manager(self):
        cctx = zstd.ZstdCompressor()

        reader = cctx.stream_reader(b"foo")
        reader.read(4)
        self.assertFalse(reader.closed)

        reader.close()
        self.assertTrue(reader.closed)
        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(1)

    def test_not_implemented(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"foo" * 60) as reader:
            with self.assertRaises(io.UnsupportedOperation):
                reader.readline()

            with self.assertRaises(io.UnsupportedOperation):
                reader.readlines()

            with self.assertRaises(io.UnsupportedOperation):
                iter(reader)

            with self.assertRaises(io.UnsupportedOperation):
                next(reader)

            with self.assertRaises(OSError):
                reader.writelines([])

            with self.assertRaises(OSError):
                reader.write(b"foo")

    def test_constant_methods(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"boo") as reader:
            self.assertTrue(reader.readable())
            self.assertFalse(reader.writable())
            self.assertFalse(reader.seekable())
            self.assertFalse(reader.isatty())
            self.assertFalse(reader.closed)
            self.assertIsNone(reader.flush())
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_read_closed(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"foo" * 60) as reader:
            reader.close()
            self.assertTrue(reader.closed)
            with self.assertRaisesRegex(ValueError, "stream is closed"):
                reader.read(10)

    def test_read_sizes(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        with cctx.stream_reader(b"foo") as reader:
            with self.assertRaisesRegex(
                ValueError, "cannot read negative amounts less than -1"
            ):
                reader.read(-2)

            self.assertEqual(reader.read(0), b"")
            self.assertEqual(reader.read(), foo)

    def test_read_buffer(self):
        cctx = zstd.ZstdCompressor()

        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        with cctx.stream_reader(source) as reader:
            self.assertEqual(reader.tell(), 0)

            # We should get entire frame in one read.
            result = reader.read(8192)
            self.assertEqual(result, frame)
            self.assertEqual(reader.tell(), len(result))
            self.assertEqual(reader.read(), b"")
            self.assertEqual(reader.tell(), len(result))

    def test_read_buffer_small_chunks(self):
        cctx = zstd.ZstdCompressor()

        source = b"foo" * 60
        chunks = []

        with cctx.stream_reader(source) as reader:
            self.assertEqual(reader.tell(), 0)

            while True:
                chunk = reader.read(1)
                if not chunk:
                    break

                chunks.append(chunk)
                self.assertEqual(reader.tell(), sum(map(len, chunks)))

        self.assertEqual(b"".join(chunks), cctx.compress(source))

    def test_read_stream(self):
        cctx = zstd.ZstdCompressor()

        source = b"".join([b"foo" * 60, b"bar" * 60, b"baz" * 60])
        frame = cctx.compress(source)

        with cctx.stream_reader(io.BytesIO(source), size=len(source)) as reader:
            self.assertEqual(reader.tell(), 0)

            chunk = reader.read(8192)
            self.assertEqual(chunk, frame)
            self.assertEqual(reader.tell(), len(chunk))
            self.assertEqual(reader.read(), b"")
            self.assertEqual(reader.tell(), len(chunk))

    def test_read_stream_small_chunks(self):
        cctx = zstd.ZstdCompressor()

        source = b"foo" * 60
        chunks = []

        with cctx.stream_reader(io.BytesIO(source), size=len(source)) as reader:
            self.assertEqual(reader.tell(), 0)

            while True:
                chunk = reader.read(1)
                if not chunk:
                    break

                chunks.append(chunk)
                self.assertEqual(reader.tell(), sum(map(len, chunks)))

        self.assertEqual(b"".join(chunks), cctx.compress(source))

    def test_read_after_exit(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"foo" * 60) as reader:
            while reader.read(8192):
                pass

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(10)

    def test_bad_size(self):
        cctx = zstd.ZstdCompressor()

        source = io.BytesIO(b"foobar")

        with cctx.stream_reader(source, size=2) as reader:
            with self.assertRaisesRegex(
                zstd.ZstdError, "Src size is incorrect"
            ):
                reader.read(10)

        # Try another compression operation.
        with cctx.stream_reader(source, size=42):
            pass

    def test_readall(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"foo" * 1024)

        reader = cctx.stream_reader(b"foo" * 1024)
        self.assertEqual(reader.readall(), frame)

    def test_readinto(self):
        cctx = zstd.ZstdCompressor()
        foo = cctx.compress(b"foo")

        reader = cctx.stream_reader(b"foo")
        with self.assertRaises(Exception):
            reader.readinto(b"foobar")

        # readinto() with sufficiently large destination.
        b = bytearray(1024)
        reader = cctx.stream_reader(b"foo")
        self.assertEqual(reader.readinto(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)
        self.assertEqual(reader.readinto(b), 0)
        self.assertEqual(b[0 : len(foo)], foo)

        # readinto() with small reads.
        b = bytearray(1024)
        reader = cctx.stream_reader(b"foo", read_size=1)
        self.assertEqual(reader.readinto(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)

        # Too small destination buffer.
        b = bytearray(2)
        reader = cctx.stream_reader(b"foo")
        self.assertEqual(reader.readinto(b), 2)
        self.assertEqual(b[:], foo[0:2])
        self.assertEqual(reader.readinto(b), 2)
        self.assertEqual(b[:], foo[2:4])
        self.assertEqual(reader.readinto(b), 2)
        self.assertEqual(b[:], foo[4:6])

    def test_readinto1(self):
        cctx = zstd.ZstdCompressor()
        foo = b"".join(cctx.read_to_iter(io.BytesIO(b"foo")))

        reader = cctx.stream_reader(b"foo")
        with self.assertRaises(Exception):
            reader.readinto1(b"foobar")

        b = bytearray(1024)
        source = CustomBytesIO(b"foo")
        reader = cctx.stream_reader(source)
        self.assertEqual(reader.readinto1(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)
        self.assertEqual(source._read_count, 2)

        # readinto1() with small reads.
        b = bytearray(1024)
        source = CustomBytesIO(b"foo")
        reader = cctx.stream_reader(source, read_size=1)
        self.assertEqual(reader.readinto1(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)
        self.assertEqual(source._read_count, 4)

    def test_readinto_tell(self):
        data = bytes(range(256)) * 2048
        cases = (
            (b"foo", False),
            (b"foo", True),
            (b"", True),
            (data, False),
            (data, True),
        )

        for method in ("readinto", "readinto1"):
            for data, stream in cases:
                for size in (1, 17, 1024):
                    with self.subTest(
                        method=method,
                        stream=stream,
                        source_size=len(data),
                        buffer_size=size,
                    ):
                        cctx = zstd.ZstdCompressor(write_checksum=True)
                        source = io.BytesIO(data) if stream else data
                        dest = bytearray(size)
                        chunks = []
                        total = 0

                        with cctx.stream_reader(
                            source, size=len(data)
                        ) as reader:
                            self.assertEqual(reader.tell(), 0)
                            while True:
                                count = getattr(reader, method)(dest)
                                total += count
                                chunks.append(bytes(dest[:count]))
                                self.assertEqual(reader.tell(), total)
                                if not count:
                                    break

                            self.assertEqual(getattr(reader, method)(dest), 0)
                            self.assertEqual(reader.tell(), total)

                        frame = b"".join(chunks)
                        self.assertEqual(
                            zstd.ZstdDecompressor().decompress(
                                frame, max_output_size=max(len(data), 1)
                            ),
                            data,
                        )

    def test_readinto_tell_mixed_reads(self):
        for method in ("readinto", "readinto1"):
            with self.subTest(method=method):
                cctx = zstd.ZstdCompressor()
                data = b"foo" * 1024
                dest = bytearray(b"!" * 1026)
                view = memoryview(dest)[1:-1]
                chunks = []

                with cctx.stream_reader(
                    io.BytesIO(data), size=len(data)
                ) as reader:
                    chunks.append(reader.read(1))
                    chunks.append(reader.read1(2))
                    total = sum(map(len, chunks))
                    self.assertEqual(reader.tell(), total)

                    while True:
                        count = getattr(reader, method)(view)
                        total += count
                        chunks.append(bytes(view[:count]))
                        self.assertEqual(reader.tell(), total)
                        self.assertEqual(dest[0], ord("!"))
                        self.assertEqual(dest[-1], ord("!"))
                        if not count:
                            break

                    self.assertEqual(reader.read(1), b"")
                    self.assertEqual(reader.read1(1), b"")
                    self.assertEqual(reader.tell(), total)

                self.assertEqual(
                    zstd.ZstdDecompressor().decompress(b"".join(chunks)), data
                )

    def test_readinto_tell_invalid_buffer(self):
        for method in ("readinto", "readinto1"):
            with self.subTest(method=method):
                reader = zstd.ZstdCompressor().stream_reader(b"foo")
                with self.assertRaises((TypeError, BufferError, ValueError)):
                    getattr(reader, method)(b"read only")
                self.assertEqual(reader.tell(), 0)
                reader.close()
                with self.assertRaisesRegex(ValueError, "stream is closed"):
                    getattr(reader, method)(bytearray(1))
                self.assertEqual(reader.tell(), 0)

    def test_read1(self):
        cctx = zstd.ZstdCompressor()
        foo = b"".join(cctx.read_to_iter(io.BytesIO(b"foo")))

        b = CustomBytesIO(b"foo")
        reader = cctx.stream_reader(b)

        self.assertEqual(reader.read1(), foo)
        self.assertEqual(b._read_count, 2)

        b = CustomBytesIO(b"foo")
        reader = cctx.stream_reader(b)

        self.assertEqual(reader.read1(0), b"")
        self.assertEqual(reader.read1(2), foo[0:2])
        self.assertEqual(b._read_count, 2)
        self.assertEqual(reader.read1(2), foo[2:4])
        self.assertEqual(reader.read1(1024), foo[4:])

    def test_close(self):
        buffer = NonClosingBytesIO(b"foo" * 1024)
        cctx = zstd.ZstdCompressor()
        reader = cctx.stream_reader(buffer)

        reader.read(3)
        self.assertFalse(reader.closed)
        self.assertFalse(buffer.closed)
        reader.close()
        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(3)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with reader:
                pass

        # Context manager exit should close stream.
        buffer = io.BytesIO(b"foo" * 1024)
        reader = cctx.stream_reader(buffer)

        with reader:
            reader.read(3)

        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        # Context manager exit should close stream if an exception raised.
        buffer = io.BytesIO(b"foo" * 1024)
        reader = cctx.stream_reader(buffer)

        with self.assertRaisesRegex(Exception, "ignore"):
            with reader:
                reader.read(3)
                raise Exception("ignore")

        self.assertTrue(reader.closed)
        self.assertTrue(buffer.closed)

        # Test with non-file source.
        with cctx.stream_reader(b"foo" * 1024) as reader:
            reader.read(3)
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_close_closefd_false(self):
        buffer = NonClosingBytesIO(b"foo" * 1024)
        cctx = zstd.ZstdCompressor()
        reader = cctx.stream_reader(buffer, closefd=False)

        reader.read(3)
        self.assertFalse(reader.closed)
        self.assertFalse(buffer.closed)
        reader.close()
        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            reader.read(3)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with reader:
                pass

        # Context manager exit should close stream.
        buffer = io.BytesIO(b"foo" * 1024)
        reader = cctx.stream_reader(buffer, closefd=False)

        with reader:
            reader.read(3)

        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        # Context manager exit should close stream if an exception raised.
        buffer = io.BytesIO(b"foo" * 1024)
        reader = cctx.stream_reader(buffer, closefd=False)

        with self.assertRaisesRegex(Exception, "ignore"):
            with reader:
                reader.read(3)
                raise Exception("ignore")

        self.assertTrue(reader.closed)
        self.assertFalse(buffer.closed)

        # Test with non-file source variant.
        with cctx.stream_reader(b"foo" * 1024, closefd=False) as reader:
            reader.read(3)
            self.assertFalse(reader.closed)

        self.assertTrue(reader.closed)

    def test_write_exception(self):
        b = CustomBytesIO()
        b.write_exception = IOError("write")

        cctx = zstd.ZstdCompressor()

        writer = cctx.stream_writer(b)
        # Initial write won't issue write() to underlying stream.
        writer.write(b"foo")

        with self.assertRaisesRegex(IOError, "write"):
            writer.flush()
