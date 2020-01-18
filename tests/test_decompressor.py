import io
import os
import random
import struct
import sys
import tempfile
import unittest

import zstandard as zstd

from .common import (
    generate_samples,
    make_cffi,
    NonClosingBytesIO,
    OpCountingBytesIO,
    TestCase,
)


if sys.version_info[0] >= 3:
    next = lambda it: it.__next__()
else:
    next = lambda it: it.next()


@make_cffi
class TestFrameHeaderSize(TestCase):
    def test_empty(self):
        with self.assertRaisesRegex(
            zstd.ZstdError,
            "could not determine frame header size: Src size " "is incorrect",
        ):
            zstd.frame_header_size(b"")

    def test_too_small(self):
        with self.assertRaisesRegex(
            zstd.ZstdError,
            "could not determine frame header size: Src size " "is incorrect",
        ):
            zstd.frame_header_size(b"foob")

    def test_basic(self):
        # It doesn't matter that it isn't a valid frame.
        self.assertEqual(zstd.frame_header_size(b"long enough but no magic"), 6)


@make_cffi
class TestFrameContentSize(TestCase):
    def test_empty(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"")

    def test_too_small(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"foob")

    def test_bad_frame(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"invalid frame header")

    def test_unknown(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        frame = cctx.compress(b"foobar")

        self.assertEqual(zstd.frame_content_size(frame), -1)

    def test_empty(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"")

        self.assertEqual(zstd.frame_content_size(frame), 0)

    def test_basic(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"foobar")

        self.assertEqual(zstd.frame_content_size(frame), 6)


@make_cffi
class TestDecompressor(TestCase):
    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()

        self.assertGreater(dctx.memory_size(), 100)


@make_cffi
class TestDecompressor_decompress(TestCase):
    def test_empty_input(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(
            zstd.ZstdError, "error determining content size from frame header"
        ):
            dctx.decompress(b"")

    def test_invalid_input(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(
            zstd.ZstdError, "error determining content size from frame header"
        ):
            dctx.decompress(b"foobar")

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
            self.assertEqual(dctx.decompress(source), b"foo")

    def test_no_content_size_in_frame(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        with self.assertRaisesRegex(
            zstd.ZstdError, "could not determine content size in frame header"
        ):
            dctx.decompress(compressed)

    def test_content_size_present(self):
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        self.assertEqual(decompressed, b"foobar")

    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(b"")

        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)

        self.assertEqual(decompressed, b"")

    def test_max_output_size(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        source = b"foobar" * 256
        compressed = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        # Will fit into buffer exactly the size of input.
        decompressed = dctx.decompress(compressed, max_output_size=len(source))
        self.assertEqual(decompressed, source)

        # Input size - 1 fails
        with self.assertRaisesRegex(
            zstd.ZstdError, "decompression error: did not decompress full frame"
        ):
            dctx.decompress(compressed, max_output_size=len(source) - 1)

        # Input size + 1 works
        decompressed = dctx.decompress(
            compressed, max_output_size=len(source) + 1
        )
        self.assertEqual(decompressed, source)

        # A much larger buffer works.
        decompressed = dctx.decompress(
            compressed, max_output_size=len(source) * 64
        )
        self.assertEqual(decompressed, source)

    def test_stupidly_large_output_buffer(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b"foobar" * 256)
        dctx = zstd.ZstdDecompressor()

        # Will get OverflowError on some Python distributions that can't
        # handle really large integers.
        with self.assertRaises((MemoryError, OverflowError)):
            dctx.decompress(compressed, max_output_size=2 ** 62)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        orig = b"foobar" * 16384
        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        compressed = cctx.compress(orig)

        dctx = zstd.ZstdDecompressor(dict_data=d)
        decompressed = dctx.decompress(compressed)

        self.assertEqual(decompressed, orig)

    def test_dictionary_multiple(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        sources = (b"foobar" * 8192, b"foo" * 8192, b"bar" * 8192)
        compressed = []
        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        for source in sources:
            compressed.append(cctx.compress(source))

        dctx = zstd.ZstdDecompressor(dict_data=d)
        for i in range(len(sources)):
            decompressed = dctx.decompress(compressed[i])
            self.assertEqual(decompressed, sources[i])

    def test_max_window_size(self):
        with open(__file__, "rb") as fh:
            source = fh.read()

        # If we write a content size, the decompressor engages single pass
        # mode and the window size doesn't come into play.
        cctx = zstd.ZstdCompressor(write_content_size=False)
        frame = cctx.compress(source)

        dctx = zstd.ZstdDecompressor(max_window_size=2 ** zstd.WINDOWLOG_MIN)

        with self.assertRaisesRegex(
            zstd.ZstdError,
            "decompression error: Frame requires too much memory",
        ):
            dctx.decompress(frame, max_output_size=len(source))


@make_cffi
class TestDecompressor_copy_stream(TestCase):
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
        source = OpCountingBytesIO(
            zstd.ZstdCompressor().compress(b"foobarfoobar")
        )

        dest = OpCountingBytesIO()
        dctx = zstd.ZstdDecompressor()
        r, w = dctx.copy_stream(source, dest, read_size=1, write_size=1)

        self.assertEqual(r, len(source.getvalue()))
        self.assertEqual(w, len(b"foobarfoobar"))
        self.assertEqual(source._read_count, len(source.getvalue()) + 1)
        self.assertEqual(dest._write_count, len(dest.getvalue()))


@make_cffi
class TestDecompressor_stream_reader(TestCase):
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
            self.assertTrue(reader.seekable())
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
                ValueError, "cannot seek to negative position"
            ):
                reader.seek(-1, os.SEEK_SET)

            reader.read(1)

            with self.assertRaisesRegex(
                ValueError, "cannot seek zstd decompression stream backwards"
            ):
                reader.seek(0, os.SEEK_SET)

            with self.assertRaisesRegex(
                ValueError, "cannot seek zstd decompression stream backwards"
            ):
                reader.seek(-1, os.SEEK_CUR)

            with self.assertRaisesRegex(
                ValueError,
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

        with reader:
            with self.assertRaisesRegex(ValueError, "stream is closed"):
                reader.read(100)

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

        b = OpCountingBytesIO(foo)
        reader = dctx.stream_reader(b)

        self.assertEqual(reader.read1(), b"foo")
        self.assertEqual(b._read_count, 1)

        b = OpCountingBytesIO(foo)
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


@make_cffi
class TestDecompressor_decompressobj(TestCase):
    def test_simple(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        self.assertEqual(dobj.decompress(data), b"foobar")
        self.assertIsNone(dobj.flush())
        self.assertIsNone(dobj.flush(10))
        self.assertIsNone(dobj.flush(length=100))

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
            self.assertIsNone(dobj.flush())
            self.assertIsNone(dobj.flush(10))
            self.assertIsNone(dobj.flush(length=100))
            self.assertEqual(dobj.decompress(source), b"foo")
            self.assertIsNone(dobj.flush())

    def test_reuse(self):
        data = zstd.ZstdCompressor(level=1).compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        dobj.decompress(data)

        with self.assertRaisesRegex(
            zstd.ZstdError, "cannot use a decompressobj"
        ):
            dobj.decompress(data)
            self.assertIsNone(dobj.flush())

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


def decompress_via_writer(data):
    buffer = io.BytesIO()
    dctx = zstd.ZstdDecompressor()
    decompressor = dctx.stream_writer(buffer)
    decompressor.write(data)

    return buffer.getvalue()


@make_cffi
class TestDecompressor_stream_writer(TestCase):
    def test_io_api(self):
        buffer = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        writer = dctx.stream_writer(buffer)

        self.assertFalse(writer.closed)
        self.assertFalse(writer.isatty())
        self.assertFalse(writer.readable())

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
        buffer = NonClosingBytesIO()
        writer = dctx.stream_writer(buffer)

        with writer:
            writer.write(foo)

        self.assertTrue(writer.closed)
        self.assertEqual(buffer.getvalue(), b"foo")

    def test_flush(self):
        buffer = OpCountingBytesIO()
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

            buffer = NonClosingBytesIO()

            with dctx.stream_writer(buffer) as decompressor:
                self.assertEqual(decompressor.write(source), 3)

            self.assertEqual(buffer.getvalue(), b"foo")

            buffer = io.BytesIO()
            writer = dctx.stream_writer(buffer, write_return_read=True)
            self.assertEqual(writer.write(source), len(source))
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

        buffer = NonClosingBytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_writer(buffer) as decompressor:
            pos = 0
            while pos < len(compressed):
                pos2 = pos + 8192
                decompressor.write(compressed[pos:pos2])
                pos += 8192
        self.assertEqual(buffer.getvalue(), orig)

        # Again with write_return_read=True
        buffer = io.BytesIO()
        writer = dctx.stream_writer(buffer, write_return_read=True)
        pos = 0
        while pos < len(compressed):
            pos2 = pos + 8192
            chunk = compressed[pos:pos2]
            self.assertEqual(writer.write(chunk), len(chunk))
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
        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(dict_data=d)
        with cctx.stream_writer(buffer) as compressor:
            self.assertEqual(compressor.write(orig), 0)

        compressed = buffer.getvalue()
        buffer = io.BytesIO()

        dctx = zstd.ZstdDecompressor(dict_data=d)
        decompressor = dctx.stream_writer(buffer)
        self.assertEqual(decompressor.write(compressed), len(orig))
        self.assertEqual(buffer.getvalue(), orig)

        buffer = NonClosingBytesIO()

        with dctx.stream_writer(buffer) as decompressor:
            self.assertEqual(decompressor.write(compressed), len(orig))

        self.assertEqual(buffer.getvalue(), orig)

    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()
        buffer = io.BytesIO()

        decompressor = dctx.stream_writer(buffer)
        size = decompressor.memory_size()
        self.assertGreater(size, 100000)

        with dctx.stream_writer(buffer) as decompressor:
            size = decompressor.memory_size()

        self.assertGreater(size, 100000)

    def test_write_size(self):
        source = zstd.ZstdCompressor().compress(b"foobarfoobar")
        dest = OpCountingBytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_writer(dest, write_size=1) as decompressor:
            s = struct.Struct(">B")
            for c in source:
                if not isinstance(c, str):
                    c = s.pack(c)
                decompressor.write(c)

        self.assertEqual(dest.getvalue(), b"foobarfoobar")
        self.assertEqual(dest._write_count, len(dest.getvalue()))


@make_cffi
class TestDecompressor_read_to_iter(TestCase):
    def test_type_validation(self):
        dctx = zstd.ZstdDecompressor()

        # Object with read() works.
        dctx.read_to_iter(io.BytesIO())

        # Buffer protocol works.
        dctx.read_to_iter(b"foobar")

        with self.assertRaisesRegex(
            ValueError, "must pass an object with a read"
        ):
            b"".join(dctx.read_to_iter(True))

    def test_empty_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO()
        it = dctx.read_to_iter(source)
        # TODO this is arguably wrong. Should get an error about missing frame foo.
        with self.assertRaises(StopIteration):
            next(it)

        it = dctx.read_to_iter(b"")
        with self.assertRaises(StopIteration):
            next(it)

    def test_invalid_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO(b"foobar")
        it = dctx.read_to_iter(source)
        with self.assertRaisesRegex(zstd.ZstdError, "Unknown frame descriptor"):
            next(it)

        it = dctx.read_to_iter(b"foobar")
        with self.assertRaisesRegex(zstd.ZstdError, "Unknown frame descriptor"):
            next(it)

    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        empty = cctx.compress(b"")

        source = io.BytesIO(empty)
        source.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(source)

        # No chunks should be emitted since there is no data.
        with self.assertRaises(StopIteration):
            next(it)

        # Again for good measure.
        with self.assertRaises(StopIteration):
            next(it)

    def test_skip_bytes_too_large(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(
            ValueError, "skip_bytes must be smaller than read_size"
        ):
            b"".join(dctx.read_to_iter(b"", skip_bytes=1, read_size=1))

        with self.assertRaisesRegex(
            ValueError, "skip_bytes larger than first input chunk"
        ):
            b"".join(dctx.read_to_iter(b"foobar", skip_bytes=10))

    def test_skip_bytes(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        output = b"".join(dctx.read_to_iter(b"hdr" + compressed, skip_bytes=3))
        self.assertEqual(output, b"foobar")

    def test_large_output(self):
        source = io.BytesIO()
        source.write(b"f" * zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE)
        source.write(b"o")
        source.seek(0)

        cctx = zstd.ZstdCompressor(level=1)
        compressed = io.BytesIO(cctx.compress(source.getvalue()))
        compressed.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(decompressed, source.getvalue())

        # And again with buffer protocol.
        it = dctx.read_to_iter(compressed.getvalue())
        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(decompressed, source.getvalue())

    @unittest.skipUnless(
        "ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set"
    )
    def test_large_input(self):
        bytes = list(struct.Struct(">B").pack(i) for i in range(256))
        compressed = NonClosingBytesIO()
        input_size = 0
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(compressed) as compressor:
            while True:
                compressor.write(random.choice(bytes))
                input_size += 1

                have_compressed = (
                    len(compressed.getvalue())
                    > zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE
                )
                have_raw = (
                    input_size > zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE * 2
                )
                if have_compressed and have_raw:
                    break

        compressed = io.BytesIO(compressed.getvalue())
        self.assertGreater(
            len(compressed.getvalue()),
            zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE,
        )

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(len(decompressed), input_size)

        # And again with buffer protocol.
        it = dctx.read_to_iter(compressed.getvalue())

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(len(decompressed), input_size)

    def test_interesting(self):
        # Found this edge case via fuzzing.
        cctx = zstd.ZstdCompressor(level=1)

        source = io.BytesIO()

        compressed = NonClosingBytesIO()
        with cctx.stream_writer(compressed) as compressor:
            for i in range(256):
                chunk = b"\0" * 1024
                compressor.write(chunk)
                source.write(chunk)

        dctx = zstd.ZstdDecompressor()

        simple = dctx.decompress(
            compressed.getvalue(), max_output_size=len(source.getvalue())
        )
        self.assertEqual(simple, source.getvalue())

        compressed = io.BytesIO(compressed.getvalue())
        streamed = b"".join(dctx.read_to_iter(compressed))
        self.assertEqual(streamed, source.getvalue())

    def test_read_write_size(self):
        source = OpCountingBytesIO(
            zstd.ZstdCompressor().compress(b"foobarfoobar")
        )
        dctx = zstd.ZstdDecompressor()
        for chunk in dctx.read_to_iter(source, read_size=1, write_size=1):
            self.assertEqual(len(chunk), 1)

        self.assertEqual(source._read_count, len(source.getvalue()))

    def test_magic_less(self):
        params = zstd.CompressionParameters.from_level(
            1, format=zstd.FORMAT_ZSTD1_MAGICLESS
        )
        cctx = zstd.ZstdCompressor(compression_params=params)
        frame = cctx.compress(b"foobar")

        self.assertNotEqual(frame[0:4], b"\x28\xb5\x2f\xfd")

        dctx = zstd.ZstdDecompressor()
        with self.assertRaisesRegex(
            zstd.ZstdError, "error determining content size from frame header"
        ):
            dctx.decompress(frame)

        dctx = zstd.ZstdDecompressor(format=zstd.FORMAT_ZSTD1_MAGICLESS)
        res = b"".join(dctx.read_to_iter(frame))
        self.assertEqual(res, b"foobar")


@make_cffi
class TestDecompressor_content_dict_chain(TestCase):
    def test_bad_inputs_simple(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaises(TypeError):
            dctx.decompress_content_dict_chain(b"foo")

        with self.assertRaises(TypeError):
            dctx.decompress_content_dict_chain((b"foo", b"bar"))

        with self.assertRaisesRegex(ValueError, "empty input chain"):
            dctx.decompress_content_dict_chain([])

        with self.assertRaisesRegex(ValueError, "chunk 0 must be bytes"):
            dctx.decompress_content_dict_chain([u"foo"])

        with self.assertRaisesRegex(ValueError, "chunk 0 must be bytes"):
            dctx.decompress_content_dict_chain([True])

        with self.assertRaisesRegex(
            ValueError, "chunk 0 is too small to contain a zstd frame"
        ):
            dctx.decompress_content_dict_chain([zstd.FRAME_HEADER])

        with self.assertRaisesRegex(
            ValueError, "chunk 0 is not a valid zstd frame"
        ):
            dctx.decompress_content_dict_chain([b"foo" * 8])

        no_size = zstd.ZstdCompressor(write_content_size=False).compress(
            b"foo" * 64
        )

        with self.assertRaisesRegex(
            ValueError, "chunk 0 missing content size in frame"
        ):
            dctx.decompress_content_dict_chain([no_size])

        # Corrupt first frame.
        frame = zstd.ZstdCompressor().compress(b"foo" * 64)
        frame = frame[0:12] + frame[15:]
        with self.assertRaisesRegex(
            zstd.ZstdError, "chunk 0 did not decompress full frame"
        ):
            dctx.decompress_content_dict_chain([frame])

    def test_bad_subsequent_input(self):
        initial = zstd.ZstdCompressor().compress(b"foo" * 64)

        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(ValueError, "chunk 1 must be bytes"):
            dctx.decompress_content_dict_chain([initial, u"foo"])

        with self.assertRaisesRegex(ValueError, "chunk 1 must be bytes"):
            dctx.decompress_content_dict_chain([initial, None])

        with self.assertRaisesRegex(
            ValueError, "chunk 1 is too small to contain a zstd frame"
        ):
            dctx.decompress_content_dict_chain([initial, zstd.FRAME_HEADER])

        with self.assertRaisesRegex(
            ValueError, "chunk 1 is not a valid zstd frame"
        ):
            dctx.decompress_content_dict_chain([initial, b"foo" * 8])

        no_size = zstd.ZstdCompressor(write_content_size=False).compress(
            b"foo" * 64
        )

        with self.assertRaisesRegex(
            ValueError, "chunk 1 missing content size in frame"
        ):
            dctx.decompress_content_dict_chain([initial, no_size])

        # Corrupt second frame.
        cctx = zstd.ZstdCompressor(
            dict_data=zstd.ZstdCompressionDict(b"foo" * 64)
        )
        frame = cctx.compress(b"bar" * 64)
        frame = frame[0:12] + frame[15:]

        with self.assertRaisesRegex(
            zstd.ZstdError, "chunk 1 did not decompress full frame"
        ):
            dctx.decompress_content_dict_chain([initial, frame])

    def test_simple(self):
        original = [
            b"foo" * 64,
            b"foobar" * 64,
            b"baz" * 64,
            b"foobaz" * 64,
            b"foobarbaz" * 64,
        ]

        chunks = []
        chunks.append(zstd.ZstdCompressor().compress(original[0]))
        for i, chunk in enumerate(original[1:]):
            d = zstd.ZstdCompressionDict(original[i])
            cctx = zstd.ZstdCompressor(dict_data=d)
            chunks.append(cctx.compress(chunk))

        for i in range(1, len(original)):
            chain = chunks[0:i]
            expected = original[i - 1]
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress_content_dict_chain(chain)
            self.assertEqual(decompressed, expected)


# TODO enable for CFFI
class TestDecompressor_multi_decompress_to_buffer(TestCase):
    def test_invalid_inputs(self):
        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        with self.assertRaises(TypeError):
            dctx.multi_decompress_to_buffer(True)

        with self.assertRaises(TypeError):
            dctx.multi_decompress_to_buffer((1, 2))

        with self.assertRaisesRegex(
            TypeError, "item 0 not a bytes like object"
        ):
            dctx.multi_decompress_to_buffer([u"foo"])

        with self.assertRaisesRegex(
            ValueError, "could not determine decompressed size of item 0"
        ):
            dctx.multi_decompress_to_buffer([b"foobarbaz"])

    def test_list_input(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(d) for d in original]

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        result = dctx.multi_decompress_to_buffer(frames)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

        self.assertEqual(result[0].offset, 0)
        self.assertEqual(len(result[0]), 12)
        self.assertEqual(result[1].offset, 12)
        self.assertEqual(len(result[1]), 18)

    def test_list_input_frame_sizes(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6, b"baz" * 8]
        frames = [cctx.compress(d) for d in original]
        sizes = struct.pack("=" + "Q" * len(original), *map(len, original))

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        result = dctx.multi_decompress_to_buffer(
            frames, decompressed_sizes=sizes
        )

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

    def test_buffer_with_segments_input(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(d) for d in original]

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        segments = struct.pack(
            "=QQQQ", 0, len(frames[0]), len(frames[0]), len(frames[1])
        )
        b = zstd.BufferWithSegments(b"".join(frames), segments)

        result = dctx.multi_decompress_to_buffer(b)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result[0].offset, 0)
        self.assertEqual(len(result[0]), 12)
        self.assertEqual(result[1].offset, 12)
        self.assertEqual(len(result[1]), 18)

    def test_buffer_with_segments_sizes(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        original = [b"foo" * 4, b"bar" * 6, b"baz" * 8]
        frames = [cctx.compress(d) for d in original]
        sizes = struct.pack("=" + "Q" * len(original), *map(len, original))

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        segments = struct.pack(
            "=QQQQQQ",
            0,
            len(frames[0]),
            len(frames[0]),
            len(frames[1]),
            len(frames[0]) + len(frames[1]),
            len(frames[2]),
        )
        b = zstd.BufferWithSegments(b"".join(frames), segments)

        result = dctx.multi_decompress_to_buffer(b, decompressed_sizes=sizes)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

    def test_buffer_with_segments_collection_input(self):
        cctx = zstd.ZstdCompressor()

        original = [
            b"foo0" * 2,
            b"foo1" * 3,
            b"foo2" * 4,
            b"foo3" * 5,
            b"foo4" * 6,
        ]

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        frames = cctx.multi_compress_to_buffer(original)

        # Check round trip.
        dctx = zstd.ZstdDecompressor()

        decompressed = dctx.multi_decompress_to_buffer(frames, threads=3)

        self.assertEqual(len(decompressed), len(original))

        for i, data in enumerate(original):
            self.assertEqual(data, decompressed[i].tobytes())

        # And a manual mode.
        b = b"".join([frames[0].tobytes(), frames[1].tobytes()])
        b1 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQ", 0, len(frames[0]), len(frames[0]), len(frames[1])
            ),
        )

        b = b"".join(
            [frames[2].tobytes(), frames[3].tobytes(), frames[4].tobytes()]
        )
        b2 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQQQ",
                0,
                len(frames[2]),
                len(frames[2]),
                len(frames[3]),
                len(frames[2]) + len(frames[3]),
                len(frames[4]),
            ),
        )

        c = zstd.BufferWithSegmentsCollection(b1, b2)

        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.multi_decompress_to_buffer(c)

        self.assertEqual(len(decompressed), 5)
        for i in range(5):
            self.assertEqual(decompressed[i].tobytes(), original[i])

    def test_dict(self):
        d = zstd.train_dictionary(16384, generate_samples(), k=64, d=16)

        cctx = zstd.ZstdCompressor(dict_data=d, level=1)
        frames = [cctx.compress(s) for s in generate_samples()]

        dctx = zstd.ZstdDecompressor(dict_data=d)

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        result = dctx.multi_decompress_to_buffer(frames)

        self.assertEqual([o.tobytes() for o in result], generate_samples())

    def test_multiple_threads(self):
        cctx = zstd.ZstdCompressor()

        frames = []
        frames.extend(cctx.compress(b"x" * 64) for i in range(256))
        frames.extend(cctx.compress(b"y" * 64) for i in range(256))

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        result = dctx.multi_decompress_to_buffer(frames, threads=-1)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), 2 * 64 * 256)
        self.assertEqual(result[0].tobytes(), b"x" * 64)
        self.assertEqual(result[256].tobytes(), b"y" * 64)

    def test_item_failure(self):
        cctx = zstd.ZstdCompressor()
        frames = [cctx.compress(b"x" * 128), cctx.compress(b"y" * 128)]

        frames[1] = frames[1][0:15] + b"extra" + frames[1][15:]

        dctx = zstd.ZstdDecompressor()

        if not hasattr(dctx, "multi_decompress_to_buffer"):
            self.skipTest("multi_decompress_to_buffer not available")

        with self.assertRaisesRegex(
            zstd.ZstdError,
            "error decompressing item 1: ("
            "Corrupted block|"
            "Destination buffer is too small)",
        ):
            dctx.multi_decompress_to_buffer(frames)

        with self.assertRaisesRegex(
            zstd.ZstdError,
            "error decompressing item 1: ("
            "Corrupted block|"
            "Destination buffer is too small)",
        ):
            dctx.multi_decompress_to_buffer(frames, threads=2)
