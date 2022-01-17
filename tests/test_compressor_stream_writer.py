import hashlib
import io
import os
import tarfile
import tempfile
import unittest

import zstandard as zstd

from .common import (
    NonClosingBytesIO,
    CustomBytesIO,
)


class TestCompressor_stream_writer(unittest.TestCase):
    def test_io_api(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        writer = cctx.stream_writer(buffer)

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
        buffer = CustomBytesIO()
        writer = cctx.stream_writer(buffer)

        with writer:
            writer.write(b"foo")

        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

        # Context manager exit should close stream if an exception raised.
        buffer = CustomBytesIO()
        writer = cctx.stream_writer(buffer)

        with self.assertRaisesRegex(Exception, "ignore"):
            with writer:
                writer.write(b"foo")
                raise Exception("ignore")

        self.assertTrue(writer.closed)
        self.assertTrue(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

    def test_close_closefd_false(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        writer = cctx.stream_writer(buffer, closefd=False)

        writer.write(b"foo" * 1024)
        self.assertFalse(writer.closed)
        self.assertFalse(buffer.closed)
        writer.close()
        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)

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

        # Context manager exit should not close stream.
        buffer = CustomBytesIO()
        writer = cctx.stream_writer(buffer, closefd=False)

        with writer:
            writer.write(b"foo")

        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

        # Context manager exit should close stream if an exception raised.
        buffer = CustomBytesIO()
        writer = cctx.stream_writer(buffer, closefd=False)

        with self.assertRaisesRegex(Exception, "ignore"):
            with writer:
                writer.write(b"foo")
                raise Exception("ignore")

        self.assertTrue(writer.closed)
        self.assertFalse(buffer.closed)
        self.assertEqual(buffer._flush_count, 0)

    def test_empty(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        with cctx.stream_writer(buffer, closefd=False) as compressor:
            compressor.write(b"")

        result = buffer.getvalue()
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")

        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Test without context manager.
        buffer = io.BytesIO()
        compressor = cctx.stream_writer(buffer)
        self.assertEqual(compressor.write(b""), 0)
        self.assertEqual(buffer.getvalue(), b"")
        self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 9)
        result = buffer.getvalue()
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")

        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Test write_return_read=False
        compressor = cctx.stream_writer(buffer, write_return_read=False)
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
            buffer = io.BytesIO()
            with cctx.stream_writer(buffer, closefd=False) as compressor:
                compressor.write(source)

            self.assertEqual(buffer.getvalue(), expected)

            compressor = cctx.stream_writer(buffer, write_return_read=False)
            self.assertEqual(compressor.write(source), 0)

    def test_multiple_compress(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=5)
        with cctx.stream_writer(buffer, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foo"), 3)
            self.assertEqual(compressor.write(b"bar"), 3)
            self.assertEqual(compressor.write(b"x" * 8192), 8192)

        result = buffer.getvalue()
        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x00\x58\x75\x00\x00\x38\x66\x6f"
            b"\x6f\x62\x61\x72\x78\x01\x00\xfc\xdf\x03\x23",
        )

        # Test without context manager.
        buffer = io.BytesIO()
        compressor = cctx.stream_writer(buffer)
        self.assertEqual(compressor.write(b"foo"), 3)
        self.assertEqual(compressor.write(b"bar"), 3)
        self.assertEqual(compressor.write(b"x" * 8192), 8192)
        self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 23)
        result = buffer.getvalue()
        self.assertEqual(
            result,
            b"\x28\xb5\x2f\xfd\x00\x58\x75\x00\x00\x38\x66\x6f"
            b"\x6f\x62\x61\x72\x78\x01\x00\xfc\xdf\x03\x23",
        )

        # Test with write_return_read=False.
        compressor = cctx.stream_writer(buffer, write_return_read=False)
        self.assertEqual(compressor.write(b"foo"), 0)
        self.assertEqual(compressor.write(b"barbiz"), 0)
        self.assertEqual(compressor.write(b"x" * 8192), 0)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b"foo" * 64)
            samples.append(b"bar" * 64)
            samples.append(b"foobar" * 64)

        d = zstd.train_dictionary(8192, samples)

        h = hashlib.sha1(d.as_bytes()).hexdigest()
        self.assertEqual(h, "a46d2f7a3bc3357c9d717d3dadf9a26fde23e93d")

        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=9, dict_data=d)
        with cctx.stream_writer(buffer, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foo"), 3)
            self.assertEqual(compressor.write(b"bar"), 3)
            self.assertEqual(compressor.write(b"foo" * 16384), 3 * 16384)

        compressed = buffer.getvalue()

        params = zstd.get_frame_parameters(compressed)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 4194304)
        self.assertEqual(params.dict_id, d.dict_id())
        self.assertFalse(params.has_checksum)

        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, "f8ca6ebe269a822615e86d710c74d61cb4d4e3ca")

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

        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(compression_params=params)
        with cctx.stream_writer(buffer, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foo"), 3)
            self.assertEqual(compressor.write(b"bar"), 3)
            self.assertEqual(compressor.write(b"foobar" * 16384), 6 * 16384)

        compressed = buffer.getvalue()

        params = zstd.get_frame_parameters(compressed)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1048576)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, "dd4bb7d37c1a0235b38a2f6b462814376843ef0b")

    def test_write_checksum(self):
        no_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(no_checksum, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobar"), 6)

        with_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        with cctx.stream_writer(with_checksum, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobar"), 6)

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
        no_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        with cctx.stream_writer(no_size, closefd=False) as compressor:
            self.assertEqual(
                compressor.write(b"foobar" * 256), len(b"foobar" * 256)
            )

        with_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(with_size, closefd=False) as compressor:
            self.assertEqual(
                compressor.write(b"foobar" * 256), len(b"foobar" * 256)
            )

        # Source size is not known in streaming mode, so header not
        # written.
        self.assertEqual(len(with_size.getvalue()), len(no_size.getvalue()))

        # Declaring size will write the header.
        with_size = io.BytesIO()
        with cctx.stream_writer(
            with_size, size=len(b"foobar" * 256), closefd=False
        ) as compressor:
            self.assertEqual(
                compressor.write(b"foobar" * 256), len(b"foobar" * 256)
            )

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

        with_dict_id = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        with cctx.stream_writer(with_dict_id, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobarfoobar"), 12)

        self.assertEqual(with_dict_id.getvalue()[4:5], b"\x03")

        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_dict_id=False)
        no_dict_id = io.BytesIO()
        with cctx.stream_writer(no_dict_id, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobarfoobar"), 12)

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
        dest = CustomBytesIO()
        with cctx.stream_writer(
            dest, write_size=1, closefd=False
        ) as compressor:
            self.assertEqual(compressor.write(b"foo"), 3)
            self.assertEqual(compressor.write(b"bar"), 3)
            self.assertEqual(compressor.write(b"foobar"), 6)

        self.assertEqual(len(dest.getvalue()), dest._write_count)

    def test_flush_repeated(self):
        cctx = zstd.ZstdCompressor(level=3)
        dest = CustomBytesIO()
        with cctx.stream_writer(dest, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foo"), 3)
            self.assertEqual(dest._write_count, 0)
            self.assertEqual(compressor.flush(), 12)
            self.assertEqual(dest._flush_count, 1)
            self.assertEqual(dest._write_count, 1)
            self.assertEqual(compressor.write(b"bar"), 3)
            self.assertEqual(dest._write_count, 1)
            self.assertEqual(compressor.flush(), 6)
            self.assertEqual(dest._flush_count, 2)
            self.assertEqual(dest._write_count, 2)
            self.assertEqual(compressor.write(b"baz"), 3)

        self.assertEqual(dest._write_count, 3)
        self.assertEqual(dest._flush_count, 2)

    def test_flush_empty_block(self):
        cctx = zstd.ZstdCompressor(level=3, write_checksum=True)
        dest = CustomBytesIO()
        with cctx.stream_writer(dest, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 8192), 6 * 8192)
            count = dest._write_count
            offset = dest.tell()
            self.assertEqual(compressor.flush(), 23)
            self.assertEqual(dest._flush_count, 1)
            self.assertGreater(dest._write_count, count)
            self.assertGreater(dest.tell(), offset)
            offset = dest.tell()
            # Ending the write here should cause an empty block to be written
            # to denote end of frame.

        self.assertEqual(dest._flush_count, 1)

        trailing = dest.getvalue()[offset:]
        # 3 bytes block header + 4 bytes frame checksum
        self.assertEqual(len(trailing), 7)

        header = trailing[0:3]
        self.assertEqual(header, b"\x01\x00\x00")

    def test_flush_frame(self):
        cctx = zstd.ZstdCompressor(level=3)
        dest = CustomBytesIO()

        with cctx.stream_writer(dest, closefd=False) as compressor:
            self.assertEqual(compressor.write(b"foobar" * 8192), 6 * 8192)
            self.assertEqual(compressor.flush(zstd.FLUSH_FRAME), 23)
            self.assertEqual(dest._flush_count, 1)
            compressor.write(b"biz" * 16384)

        self.assertEqual(dest._flush_count, 1)

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
        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor(threads=2)
        with cctx.stream_writer(dest, closefd=False) as compressor:
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
        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        with cctx.stream_writer(dest, closefd=False) as compressor:
            with tarfile.open("tf", mode="w|", fileobj=compressor) as tf:
                tf.add(__file__, "test_compressor.py")

        dest = io.BytesIO(dest.getvalue())

        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(dest) as reader:
            with tarfile.open(mode="r|", fileobj=reader) as tf:
                for member in tf:
                    self.assertEqual(member.name, "test_compressor.py")
