import hashlib
import io
import os
import struct
import sys
import tarfile
import tempfile
import unittest

import zstandard as zstd

from .common import (
    make_cffi,
    NonClosingBytesIO,
    OpCountingBytesIO,
    TestCase,
)


if sys.version_info[0] >= 3:
    next = lambda it: it.__next__()
else:
    next = lambda it: it.next()


def multithreaded_chunk_size(level, source_size=0):
    params = zstd.ZstdCompressionParameters.from_level(
        level, source_size=source_size
    )

    return 1 << (params.window_log + 2)


@make_cffi
class TestCompressor(TestCase):
    def test_level_bounds(self):
        with self.assertRaises(ValueError):
            zstd.ZstdCompressor(level=23)

    def test_memory_size(self):
        cctx = zstd.ZstdCompressor(level=1)
        self.assertGreater(cctx.memory_size(), 100)


@make_cffi
class TestCompressor_compress(TestCase):
    def test_compress_empty(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        result = cctx.compress(b"")
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00")
        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 524288)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum, 0)

        cctx = zstd.ZstdCompressor()
        result = cctx.compress(b"")
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x20\x00\x01\x00\x00")
        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, 0)

    def test_input_types(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        expected = b"\x28\xb5\x2f\xfd\x00\x00\x19\x00\x00\x66\x6f\x6f"

        mutable_array = bytearray(3)
        mutable_array[:] = b"foo"

        sources = [
            memoryview(b"foo"),
            bytearray(b"foo"),
            mutable_array,
        ]

        for source in sources:
            self.assertEqual(cctx.compress(source), expected)

    def test_compress_large(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct(">B").pack(i) * 16384)

        cctx = zstd.ZstdCompressor(level=3, write_content_size=False)
        result = cctx.compress(b"".join(chunks))
        self.assertEqual(len(result), 999)
        self.assertEqual(result[0:4], b"\x28\xb5\x2f\xfd")

        # This matches the test for read_to_iter() below.
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        result = cctx.compress(
            b"f" * zstd.COMPRESSION_RECOMMENDED_INPUT_SIZE + b"o"
        )
        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x00\x40\x54\x00\x00"
            b"\x10\x66\x66\x01\x00\xfb\xff\x39\xc0"
            b"\x02\x09\x00\x00\x6f",
        )

    def test_negative_level(self):
        cctx = zstd.ZstdCompressor(level=-4)
        result = cctx.compress(b"foo" * 256)

    def test_no_magic(self):
        params = zstd.ZstdCompressionParameters.from_level(
            1, format=zstd.FORMAT_ZSTD1
        )
        cctx = zstd.ZstdCompressor(compression_params=params)
        magic = cctx.compress(b"foobar")

        params = zstd.ZstdCompressionParameters.from_level(
            1, format=zstd.FORMAT_ZSTD1_MAGICLESS
        )
        cctx = zstd.ZstdCompressor(compression_params=params)
        no_magic = cctx.compress(b"foobar")

        self.assertEqual(magic[0:4], b"\x28\xb5\x2f\xfd")
        self.assertEqual(magic[4:], no_magic)

    def test_write_checksum(self):
        cctx = zstd.ZstdCompressor(level=1)
        no_checksum = cctx.compress(b"foobar")
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        with_checksum = cctx.compress(b"foobar")

        self.assertEqual(len(with_checksum), len(no_checksum) + 4)

        no_params = zstd.get_frame_parameters(no_checksum)
        with_params = zstd.get_frame_parameters(with_checksum)

        self.assertFalse(no_params.has_checksum)
        self.assertTrue(with_params.has_checksum)

    def test_write_content_size(self):
        cctx = zstd.ZstdCompressor(level=1)
        with_size = cctx.compress(b"foobar" * 256)
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        no_size = cctx.compress(b"foobar" * 256)

        self.assertEqual(len(with_size), len(no_size) + 1)

        no_params = zstd.get_frame_parameters(no_size)
        with_params = zstd.get_frame_parameters(with_size)
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, 1536)

    def test_no_dict_id(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(1024, samples)

        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        with_dict_id = cctx.compress(b"foobarfoobar")

        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_dict_id=False)
        no_dict_id = cctx.compress(b"foobarfoobar")

        self.assertEqual(len(with_dict_id), len(no_dict_id) + 4)

        no_params = zstd.get_frame_parameters(no_dict_id)
        with_params = zstd.get_frame_parameters(with_dict_id)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 1880053135)

    def test_compress_dict_multiple(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        cctx = zstd.ZstdCompressor(level=1, dict_data=d)

        for i in range(32):
            cctx.compress(b"foo bar foobar foo bar foobar")

    def test_dict_precompute(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)
        d.precompute_compress(level=1)

        cctx = zstd.ZstdCompressor(level=1, dict_data=d)

        for i in range(32):
            cctx.compress(b"foo bar foobar foo bar foobar")

    def test_multithreaded(self):
        chunk_size = multithreaded_chunk_size(1)
        source = b"".join([b"x" * chunk_size, b"y" * chunk_size])

        cctx = zstd.ZstdCompressor(level=1, threads=2)
        compressed = cctx.compress(source)

        params = zstd.get_frame_parameters(compressed)
        self.assertEqual(params.content_size, chunk_size * 2)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        dctx = zstd.ZstdDecompressor()
        self.assertEqual(dctx.decompress(compressed), source)

    def test_multithreaded_dict(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(1024, samples)

        cctx = zstd.ZstdCompressor(dict_data=d, threads=2)

        result = cctx.compress(b"foo")
        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, 3)
        self.assertEqual(params.dict_id, d.dict_id())

        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x23\x8f\x55\x0f\x70\x03\x19\x00\x00"
            b"\x66\x6f\x6f",
        )

    def test_multithreaded_compression_params(self):
        params = zstd.ZstdCompressionParameters.from_level(0, threads=2)
        cctx = zstd.ZstdCompressor(compression_params=params)

        result = cctx.compress(b"foo")
        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, 3)

        self.assertEqual(
            result, b"\x28\xb5\x2f\xfd\x20\x03\x19\x00\x00\x66\x6f\x6f"
        )


@make_cffi
class TestCompressor_compressobj(TestCase):
    def test_compressobj_empty(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        cobj = cctx.compressobj()
        self.assertEqual(cobj.compress(b""), b"")
        self.assertEqual(cobj.flush(), b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00")

    def test_input_types(self):
        expected = b"\x28\xb5\x2f\xfd\x00\x48\x19\x00\x00\x66\x6f\x6f"
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)

        mutable_array = bytearray(3)
        mutable_array[:] = b"foo"

        sources = [
            memoryview(b"foo"),
            bytearray(b"foo"),
            mutable_array,
        ]

        for source in sources:
            cobj = cctx.compressobj()
            self.assertEqual(cobj.compress(source), b"")
            self.assertEqual(cobj.flush(), expected)

    def test_compressobj_large(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct(">B").pack(i) * 16384)

        cctx = zstd.ZstdCompressor(level=3)
        cobj = cctx.compressobj()

        result = cobj.compress(b"".join(chunks)) + cobj.flush()
        self.assertEqual(len(result), 999)
        self.assertEqual(result[0:4], b"\x28\xb5\x2f\xfd")

        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 2097152)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

    def test_write_checksum(self):
        cctx = zstd.ZstdCompressor(level=1)
        cobj = cctx.compressobj()
        no_checksum = cobj.compress(b"foobar") + cobj.flush()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        cobj = cctx.compressobj()
        with_checksum = cobj.compress(b"foobar") + cobj.flush()

        no_params = zstd.get_frame_parameters(no_checksum)
        with_params = zstd.get_frame_parameters(with_checksum)
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertTrue(with_params.has_checksum)

        self.assertEqual(len(with_checksum), len(no_checksum) + 4)

    def test_write_content_size(self):
        cctx = zstd.ZstdCompressor(level=1)
        cobj = cctx.compressobj(size=len(b"foobar" * 256))
        with_size = cobj.compress(b"foobar" * 256) + cobj.flush()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        cobj = cctx.compressobj(size=len(b"foobar" * 256))
        no_size = cobj.compress(b"foobar" * 256) + cobj.flush()

        no_params = zstd.get_frame_parameters(no_size)
        with_params = zstd.get_frame_parameters(with_size)
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, 1536)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertFalse(with_params.has_checksum)

        self.assertEqual(len(with_size), len(no_size) + 1)

    def test_compress_after_finished(self):
        cctx = zstd.ZstdCompressor()
        cobj = cctx.compressobj()

        cobj.compress(b"foo")
        cobj.flush()

        with self.assertRaisesRegex(
            zstd.ZstdError, r"cannot call compress\(\) after compressor"
        ):
            cobj.compress(b"foo")

        with self.assertRaisesRegex(
            zstd.ZstdError, "compressor object already finished"
        ):
            cobj.flush()

    def test_flush_block_repeated(self):
        cctx = zstd.ZstdCompressor(level=1)
        cobj = cctx.compressobj()

        self.assertEqual(cobj.compress(b"foo"), b"")
        self.assertEqual(
            cobj.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK),
            b"\x28\xb5\x2f\xfd\x00\x48\x18\x00\x00foo",
        )
        self.assertEqual(cobj.compress(b"bar"), b"")
        # 3 byte header plus content.
        self.assertEqual(
            cobj.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK), b"\x18\x00\x00bar"
        )
        self.assertEqual(cobj.flush(), b"\x01\x00\x00")

    def test_flush_empty_block(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)
        cobj = cctx.compressobj()

        cobj.compress(b"foobar")
        cobj.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK)
        # No-op if no block is active (this is internal to zstd).
        self.assertEqual(cobj.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK), b"")

        trailing = cobj.flush()
        # 3 bytes block header + 4 bytes frame checksum
        self.assertEqual(len(trailing), 7)
        header = trailing[0:3]
        self.assertEqual(header, b"\x01\x00\x00")

    def test_multithreaded(self):
        source = io.BytesIO()
        source.write(b"a" * 1048576)
        source.write(b"b" * 1048576)
        source.write(b"c" * 1048576)
        source.seek(0)

        cctx = zstd.ZstdCompressor(level=1, threads=2)
        cobj = cctx.compressobj()

        chunks = []
        while True:
            d = source.read(8192)
            if not d:
                break

            chunks.append(cobj.compress(d))

        chunks.append(cobj.flush())

        compressed = b"".join(chunks)

        self.assertEqual(len(compressed), 119)

    def test_frame_progression(self):
        cctx = zstd.ZstdCompressor()

        self.assertEqual(cctx.frame_progression(), (0, 0, 0))

        cobj = cctx.compressobj()

        cobj.compress(b"foobar")
        self.assertEqual(cctx.frame_progression(), (6, 0, 0))

        cobj.flush()
        self.assertEqual(cctx.frame_progression(), (6, 6, 15))

    def test_bad_size(self):
        cctx = zstd.ZstdCompressor()

        cobj = cctx.compressobj(size=2)
        with self.assertRaisesRegex(zstd.ZstdError, "Src size is incorrect"):
            cobj.compress(b"foo")

        # Try another operation on this instance.
        with self.assertRaisesRegex(zstd.ZstdError, "Src size is incorrect"):
            cobj.compress(b"aa")

        # Try another operation on the compressor.
        cctx.compressobj(size=4)
        cctx.compress(b"foobar")


@make_cffi
class TestCompressor_copy_stream(TestCase):
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
            dest.getvalue(), b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00"
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
        source = OpCountingBytesIO(b"foobarfoobar")
        dest = OpCountingBytesIO()
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


@make_cffi
class TestCompressor_stream_reader(TestCase):
    def test_context_manager(self):
        cctx = zstd.ZstdCompressor()

        with cctx.stream_reader(b"foo") as reader:
            with self.assertRaisesRegex(
                ValueError, "cannot __enter__ multiple times"
            ):
                with reader as reader2:
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
        source = OpCountingBytesIO(b"foo")
        reader = cctx.stream_reader(source)
        self.assertEqual(reader.readinto1(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)
        self.assertEqual(source._read_count, 2)

        # readinto1() with small reads.
        b = bytearray(1024)
        source = OpCountingBytesIO(b"foo")
        reader = cctx.stream_reader(source, read_size=1)
        self.assertEqual(reader.readinto1(b), len(foo))
        self.assertEqual(b[0 : len(foo)], foo)
        self.assertEqual(source._read_count, 4)

    def test_read1(self):
        cctx = zstd.ZstdCompressor()
        foo = b"".join(cctx.read_to_iter(io.BytesIO(b"foo")))

        b = OpCountingBytesIO(b"foo")
        reader = cctx.stream_reader(b)

        self.assertEqual(reader.read1(), foo)
        self.assertEqual(b._read_count, 2)

        b = OpCountingBytesIO(b"foo")
        reader = cctx.stream_reader(b)

        self.assertEqual(reader.read1(0), b"")
        self.assertEqual(reader.read1(2), foo[0:2])
        self.assertEqual(b._read_count, 2)
        self.assertEqual(reader.read1(2), foo[2:4])
        self.assertEqual(reader.read1(1024), foo[4:])


@make_cffi
class TestCompressor_stream_writer(TestCase):
    def test_io_api(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        writer = cctx.stream_writer(buffer)

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
            writer.truncate()

        with self.assertRaises(io.UnsupportedOperation):
            writer.truncate(42)

        with self.assertRaises(io.UnsupportedOperation):
            writer.truncate(size=42)

        self.assertTrue(writer.writable())

        with self.assertRaises(NotImplementedError):
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

        self.assertFalse(writer.closed)

    def test_fileno_file(self):
        with tempfile.TemporaryFile("wb") as tf:
            cctx = zstd.ZstdCompressor()
            writer = cctx.stream_writer(tf)

            self.assertEqual(writer.fileno(), tf.fileno())

    def test_close(self):
        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        writer = cctx.stream_writer(buffer)

        writer.write(b"foo" * 1024)
        self.assertFalse(writer.closed)
        self.assertFalse(buffer.closed)
        writer.close()
        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.write(b"foo")

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            writer.flush()

        with self.assertRaisesRegex(ValueError, "stream is closed"):
            with writer:
                pass

        self.assertEqual(
            buffer.getvalue(),
            b"\x28\xb5\x2f\xfd\x00\x48\x55\x00\x00\x18\x66\x6f"
            b"\x6f\x01\x00\xfa\xd3\x77\x43",
        )

        # Context manager exit should close stream.
        buffer = io.BytesIO()
        writer = cctx.stream_writer(buffer)

        with writer:
            writer.write(b"foo")

        self.assertTrue(writer.closed)

    def test_empty(self):
        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        with cctx.stream_writer(buffer) as compressor:
            compressor.write(b"")

        result = buffer.getvalue()
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00")

        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 524288)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Test without context manager.
        buffer = io.BytesIO()
        compressor = cctx.stream_writer(buffer)
        self.assertEqual(compressor.write(b""), 0)
        self.assertEqual(buffer.getvalue(), b"")
        self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 9)
        result = buffer.getvalue()
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00")

        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 524288)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Test write_return_read=True
        compressor = cctx.stream_writer(buffer, write_return_read=True)
        self.assertEqual(compressor.write(b""), 0)

    def test_input_types(self):
        expected = b"\x28\xb5\x2f\xfd\x00\x48\x19\x00\x00\x66\x6f\x6f"
        cctx = zstd.ZstdCompressor(level=1)

        mutable_array = bytearray(3)
        mutable_array[:] = b"foo"

        sources = [
            memoryview(b"foo"),
            bytearray(b"foo"),
            mutable_array,
        ]

        for source in sources:
            buffer = NonClosingBytesIO()
            with cctx.stream_writer(buffer) as compressor:
                compressor.write(source)

            self.assertEqual(buffer.getvalue(), expected)

            compressor = cctx.stream_writer(buffer, write_return_read=True)
            self.assertEqual(compressor.write(source), len(source))

    def test_multiple_compress(self):
        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=5)
        with cctx.stream_writer(buffer) as compressor:
            self.assertEqual(compressor.write(b"foo"), 0)
            self.assertEqual(compressor.write(b"bar"), 0)
            self.assertEqual(compressor.write(b"x" * 8192), 0)

        result = buffer.getvalue()
        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x00\x58\x75\x00\x00\x38\x66\x6f"
            b"\x6f\x62\x61\x72\x78\x01\x00\xfc\xdf\x03\x23",
        )

        # Test without context manager.
        buffer = io.BytesIO()
        compressor = cctx.stream_writer(buffer)
        self.assertEqual(compressor.write(b"foo"), 0)
        self.assertEqual(compressor.write(b"bar"), 0)
        self.assertEqual(compressor.write(b"x" * 8192), 0)
        self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 23)
        result = buffer.getvalue()
        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x00\x58\x75\x00\x00\x38\x66\x6f"
            b"\x6f\x62\x61\x72\x78\x01\x00\xfc\xdf\x03\x23",
        )

        # Test with write_return_read=True.
        compressor = cctx.stream_writer(buffer, write_return_read=True)
        self.assertEqual(compressor.write(b"foo"), 3)
        self.assertEqual(compressor.write(b"barbiz"), 6)
        self.assertEqual(compressor.write(b"x" * 8192), 8192)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        h = hashlib.sha1(d.as_bytes()).hexdigest()
        self.assertEqual(h, "7a2e59a876db958f74257141045af8f912e00d4e")

        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=9, dict_data=d)
        with cctx.stream_writer(buffer) as compressor:
            self.assertEqual(compressor.write(b"foo"), 0)
            self.assertEqual(compressor.write(b"bar"), 0)
            self.assertEqual(compressor.write(b"foo" * 16384), 0)

        compressed = buffer.getvalue()

        params = zstd.get_frame_parameters(compressed)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 2097152)
        self.assertEqual(params.dict_id, d.dict_id())
        self.assertFalse(params.has_checksum)

        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, "0a7c05635061f58039727cdbe76388c6f4cfef06")

        source = b"foo" + b"bar" + (b"foo" * 16384)

        dctx = zstd.ZstdDecompressor(dict_data=d)

        self.assertEqual(
            dctx.decompress(compressed, max_output_size=len(source)), source
        )

    def test_compression_params(self):
        params = zstd.ZstdCompressionParameters(
            window_log=20,
            chain_log=6,
            hash_log=12,
            min_match=5,
            search_log=4,
            target_length=10,
            strategy=zstd.STRATEGY_FAST,
        )

        buffer = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(compression_params=params)
        with cctx.stream_writer(buffer) as compressor:
            self.assertEqual(compressor.write(b"foo"), 0)
            self.assertEqual(compressor.write(b"bar"), 0)
            self.assertEqual(compressor.write(b"foobar" * 16384), 0)

        compressed = buffer.getvalue()

        params = zstd.get_frame_parameters(compressed)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1048576)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, "dd4bb7d37c1a0235b38a2f6b462814376843ef0b")

    def test_write_checksum(self):
        no_checksum = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(no_checksum) as compressor:
            self.assertEqual(compressor.write(b"foobar"), 0)

        with_checksum = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        with cctx.stream_writer(with_checksum) as compressor:
            self.assertEqual(compressor.write(b"foobar"), 0)

        no_params = zstd.get_frame_parameters(no_checksum.getvalue())
        with_params = zstd.get_frame_parameters(with_checksum.getvalue())
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertTrue(with_params.has_checksum)

        self.assertEqual(
            len(with_checksum.getvalue()), len(no_checksum.getvalue()) + 4
        )

    def test_write_content_size(self):
        no_size = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        with cctx.stream_writer(no_size) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 256), 0)

        with_size = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(with_size) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 256), 0)

        # Source size is not known in streaming mode, so header not
        # written.
        self.assertEqual(len(with_size.getvalue()), len(no_size.getvalue()))

        # Declaring size will write the header.
        with_size = NonClosingBytesIO()
        with cctx.stream_writer(
            with_size, size=len(b"foobar" * 256)
        ) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 256), 0)

        no_params = zstd.get_frame_parameters(no_size.getvalue())
        with_params = zstd.get_frame_parameters(with_size.getvalue())
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, 1536)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, 0)
        self.assertFalse(no_params.has_checksum)
        self.assertFalse(with_params.has_checksum)

        self.assertEqual(len(with_size.getvalue()), len(no_size.getvalue()) + 1)

    def test_no_dict_id(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(1024, samples)

        with_dict_id = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        with cctx.stream_writer(with_dict_id) as compressor:
            self.assertEqual(compressor.write(b"foobarfoobar"), 0)

        self.assertEqual(with_dict_id.getvalue()[4:5], b"\x03")

        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_dict_id=False)
        no_dict_id = NonClosingBytesIO()
        with cctx.stream_writer(no_dict_id) as compressor:
            self.assertEqual(compressor.write(b"foobarfoobar"), 0)

        self.assertEqual(no_dict_id.getvalue()[4:5], b"\x00")

        no_params = zstd.get_frame_parameters(no_dict_id.getvalue())
        with_params = zstd.get_frame_parameters(with_dict_id.getvalue())
        self.assertEqual(no_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(with_params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(no_params.dict_id, 0)
        self.assertEqual(with_params.dict_id, d.dict_id())
        self.assertFalse(no_params.has_checksum)
        self.assertFalse(with_params.has_checksum)

        self.assertEqual(
            len(with_dict_id.getvalue()), len(no_dict_id.getvalue()) + 4
        )

    def test_memory_size(self):
        cctx = zstd.ZstdCompressor(level=3)
        buffer = io.BytesIO()
        with cctx.stream_writer(buffer) as compressor:
            compressor.write(b"foo")
            size = compressor.memory_size()

        self.assertGreater(size, 100000)

    def test_write_size(self):
        cctx = zstd.ZstdCompressor(level=3)
        dest = OpCountingBytesIO()
        with cctx.stream_writer(dest, write_size=1) as compressor:
            self.assertEqual(compressor.write(b"foo"), 0)
            self.assertEqual(compressor.write(b"bar"), 0)
            self.assertEqual(compressor.write(b"foobar"), 0)

        self.assertEqual(len(dest.getvalue()), dest._write_count)

    def test_flush_repeated(self):
        cctx = zstd.ZstdCompressor(level=3)
        dest = OpCountingBytesIO()
        with cctx.stream_writer(dest) as compressor:
            self.assertEqual(compressor.write(b"foo"), 0)
            self.assertEqual(dest._write_count, 0)
            self.assertEqual(compressor.flush(), 12)
            self.assertEqual(dest._write_count, 1)
            self.assertEqual(compressor.write(b"bar"), 0)
            self.assertEqual(dest._write_count, 1)
            self.assertEqual(compressor.flush(), 6)
            self.assertEqual(dest._write_count, 2)
            self.assertEqual(compressor.write(b"baz"), 0)

        self.assertEqual(dest._write_count, 3)

    def test_flush_empty_block(self):
        cctx = zstd.ZstdCompressor(level=3, write_checksum=True)
        dest = OpCountingBytesIO()
        with cctx.stream_writer(dest) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 8192), 0)
            count = dest._write_count
            offset = dest.tell()
            self.assertEqual(compressor.flush(), 23)
            self.assertGreater(dest._write_count, count)
            self.assertGreater(dest.tell(), offset)
            offset = dest.tell()
            # Ending the write here should cause an empty block to be written
            # to denote end of frame.

        trailing = dest.getvalue()[offset:]
        # 3 bytes block header + 4 bytes frame checksum
        self.assertEqual(len(trailing), 7)

        header = trailing[0:3]
        self.assertEqual(header, b"\x01\x00\x00")

    def test_flush_frame(self):
        cctx = zstd.ZstdCompressor(level=3)
        dest = OpCountingBytesIO()

        with cctx.stream_writer(dest) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 8192), 0)
            self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 23)
            compressor.write(b"biz" * 16384)

        self.assertEqual(
            dest.getvalue(),
            # Frame 1.
            b"\x28\xb5\x2f\xfd\x00\x58\x75\x00\x00\x30\x66\x6f\x6f"
            b"\x62\x61\x72\x01\x00\xf7\xbf\xe8\xa5\x08"
            # Frame 2.
            b"\x28\xb5\x2f\xfd\x00\x58\x5d\x00\x00\x18\x62\x69\x7a"
            b"\x01\x00\xfa\x3f\x75\x37\x04",
        )

    def test_bad_flush_mode(self):
        cctx = zstd.ZstdCompressor()
        dest = io.BytesIO()
        with cctx.stream_writer(dest) as compressor:
            with self.assertRaisesRegex(ValueError, "unknown flush_mode: 42"):
                compressor.flush(flush_mode=42)

    def test_multithreaded(self):
        dest = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor(threads=2)
        with cctx.stream_writer(dest) as compressor:
            compressor.write(b"a" * 1048576)
            compressor.write(b"b" * 1048576)
            compressor.write(b"c" * 1048576)

        self.assertEqual(len(dest.getvalue()), 111)

    def test_tell(self):
        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        with cctx.stream_writer(dest) as compressor:
            self.assertEqual(compressor.tell(), 0)

            for i in range(256):
                compressor.write(b"foo" * (i + 1))
                self.assertEqual(compressor.tell(), dest.tell())

    def test_bad_size(self):
        cctx = zstd.ZstdCompressor()

        dest = io.BytesIO()

        with self.assertRaisesRegex(zstd.ZstdError, "Src size is incorrect"):
            with cctx.stream_writer(dest, size=2) as compressor:
                compressor.write(b"foo")

        # Test another operation.
        with cctx.stream_writer(dest, size=42):
            pass

    def test_tarfile_compat(self):
        dest = NonClosingBytesIO()
        cctx = zstd.ZstdCompressor()
        with cctx.stream_writer(dest) as compressor:
            with tarfile.open("tf", mode="w|", fileobj=compressor) as tf:
                tf.add(__file__, "test_compressor.py")

        dest = io.BytesIO(dest.getvalue())

        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(dest) as reader:
            with tarfile.open(mode="r|", fileobj=reader) as tf:
                for member in tf:
                    self.assertEqual(member.name, "test_compressor.py")


@make_cffi
class TestCompressor_read_to_iter(TestCase):
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
        self.assertEqual(compressed, b"\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00")

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
        source = OpCountingBytesIO(b"foobarfoobar")
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


@make_cffi
class TestCompressor_chunker(TestCase):
    def test_empty(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        chunker = cctx.chunker()

        it = chunker.compress(b"")

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.finish()

        self.assertEqual(next(it), b"\x28\xb5\x2f\xfd\x00\x58\x01\x00\x00")

        with self.assertRaises(StopIteration):
            next(it)

    def test_simple_input(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        it = chunker.compress(b"foobar")

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.compress(b"baz" * 30)

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.finish()

        self.assertEqual(
            next(it),
            b"\x28\xb5\x2f\xfd\x00\x58\x7d\x00\x00\x48\x66\x6f"
            b"\x6f\x62\x61\x72\x62\x61\x7a\x01\x00\xe4\xe4\x8e",
        )

        with self.assertRaises(StopIteration):
            next(it)

    def test_input_size(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker(size=1024)

        it = chunker.compress(b"x" * 1000)

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.compress(b"y" * 24)

        with self.assertRaises(StopIteration):
            next(it)

        chunks = list(chunker.finish())

        self.assertEqual(
            chunks,
            [
                b"\x28\xb5\x2f\xfd\x60\x00\x03\x65\x00\x00\x18\x78\x78\x79\x02\x00"
                b"\xa0\x16\xe3\x2b\x80\x05"
            ],
        )

        dctx = zstd.ZstdDecompressor()

        self.assertEqual(
            dctx.decompress(b"".join(chunks)), (b"x" * 1000) + (b"y" * 24)
        )

    def test_small_chunk_size(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker(chunk_size=1)

        chunks = list(chunker.compress(b"foo" * 1024))
        self.assertEqual(chunks, [])

        chunks = list(chunker.finish())
        self.assertTrue(all(len(chunk) == 1 for chunk in chunks))

        self.assertEqual(
            b"".join(chunks),
            b"\x28\xb5\x2f\xfd\x00\x58\x55\x00\x00\x18\x66\x6f\x6f\x01\x00"
            b"\xfa\xd3\x77\x43",
        )

        dctx = zstd.ZstdDecompressor()
        self.assertEqual(
            dctx.decompress(b"".join(chunks), max_output_size=10000),
            b"foo" * 1024,
        )

    def test_input_types(self):
        cctx = zstd.ZstdCompressor()

        mutable_array = bytearray(3)
        mutable_array[:] = b"foo"

        sources = [
            memoryview(b"foo"),
            bytearray(b"foo"),
            mutable_array,
        ]

        for source in sources:
            chunker = cctx.chunker()

            self.assertEqual(list(chunker.compress(source)), [])
            self.assertEqual(
                list(chunker.finish()),
                [b"\x28\xb5\x2f\xfd\x00\x58\x19\x00\x00\x66\x6f\x6f"],
            )

    def test_flush(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        self.assertEqual(list(chunker.compress(b"foo" * 1024)), [])
        self.assertEqual(list(chunker.compress(b"bar" * 1024)), [])

        chunks1 = list(chunker.flush())

        self.assertEqual(
            chunks1,
            [
                b"\x28\xb5\x2f\xfd\x00\x58\x8c\x00\x00\x30\x66\x6f\x6f\x62\x61\x72"
                b"\x02\x00\xfa\x03\xfe\xd0\x9f\xbe\x1b\x02"
            ],
        )

        self.assertEqual(list(chunker.flush()), [])
        self.assertEqual(list(chunker.flush()), [])

        self.assertEqual(list(chunker.compress(b"baz" * 1024)), [])

        chunks2 = list(chunker.flush())
        self.assertEqual(len(chunks2), 1)

        chunks3 = list(chunker.finish())
        self.assertEqual(len(chunks2), 1)

        dctx = zstd.ZstdDecompressor()

        self.assertEqual(
            dctx.decompress(
                b"".join(chunks1 + chunks2 + chunks3), max_output_size=10000
            ),
            (b"foo" * 1024) + (b"bar" * 1024) + (b"baz" * 1024),
        )

    def test_compress_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError,
            r"cannot call compress\(\) after compression finished",
        ):
            list(chunker.compress(b"foo"))

    def test_flush_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError, r"cannot call flush\(\) after compression finished"
        ):
            list(chunker.flush())

    def test_finish_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError, r"cannot call finish\(\) after compression finished"
        ):
            list(chunker.finish())


class TestCompressor_multi_compress_to_buffer(TestCase):
    def test_invalid_inputs(self):
        cctx = zstd.ZstdCompressor()

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        with self.assertRaises(TypeError):
            cctx.multi_compress_to_buffer(True)

        with self.assertRaises(TypeError):
            cctx.multi_compress_to_buffer((1, 2))

        with self.assertRaisesRegex(
            TypeError, "item 0 not a bytes like object"
        ):
            cctx.multi_compress_to_buffer([u"foo"])

    def test_empty_input(self):
        cctx = zstd.ZstdCompressor()

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        with self.assertRaisesRegex(ValueError, "no source elements found"):
            cctx.multi_compress_to_buffer([])

        with self.assertRaisesRegex(ValueError, "source elements are empty"):
            cctx.multi_compress_to_buffer([b"", b"", b""])

    def test_list_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        original = [b"foo" * 12, b"bar" * 6]
        frames = [cctx.compress(c) for c in original]
        b = cctx.multi_compress_to_buffer(original)

        self.assertIsInstance(b, zstd.BufferWithSegmentsCollection)

        self.assertEqual(len(b), 2)
        self.assertEqual(b.size(), 44)

        self.assertEqual(b[0].tobytes(), frames[0])
        self.assertEqual(b[1].tobytes(), frames[1])

    def test_buffer_with_segments_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(c) for c in original]

        offsets = struct.pack(
            "=QQQQ", 0, len(original[0]), len(original[0]), len(original[1])
        )
        segments = zstd.BufferWithSegments(b"".join(original), offsets)

        result = cctx.multi_compress_to_buffer(segments)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.size(), 47)

        self.assertEqual(result[0].tobytes(), frames[0])
        self.assertEqual(result[1].tobytes(), frames[1])

    def test_buffer_with_segments_collection_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        original = [
            b"foo1",
            b"foo2" * 2,
            b"foo3" * 3,
            b"foo4" * 4,
            b"foo5" * 5,
        ]

        frames = [cctx.compress(c) for c in original]

        b = b"".join([original[0], original[1]])
        b1 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQ", 0, len(original[0]), len(original[0]), len(original[1])
            ),
        )
        b = b"".join([original[2], original[3], original[4]])
        b2 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQQQ",
                0,
                len(original[2]),
                len(original[2]),
                len(original[3]),
                len(original[2]) + len(original[3]),
                len(original[4]),
            ),
        )

        c = zstd.BufferWithSegmentsCollection(b1, b2)

        result = cctx.multi_compress_to_buffer(c)

        self.assertEqual(len(result), len(frames))

        for i, frame in enumerate(frames):
            self.assertEqual(result[i].tobytes(), frame)

    def test_multiple_threads(self):
        # threads argument will cause multi-threaded ZSTD APIs to be used, which will
        # make output different.
        refcctx = zstd.ZstdCompressor(write_checksum=True)
        reference = [refcctx.compress(b"x" * 64), refcctx.compress(b"y" * 64)]

        cctx = zstd.ZstdCompressor(write_checksum=True)

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        frames = []
        frames.extend(b"x" * 64 for i in range(256))
        frames.extend(b"y" * 64 for i in range(256))

        result = cctx.multi_compress_to_buffer(frames, threads=-1)

        self.assertEqual(len(result), 512)
        for i in range(512):
            if i < 256:
                self.assertEqual(result[i].tobytes(), reference[0])
            else:
                self.assertEqual(result[i].tobytes(), reference[1])
