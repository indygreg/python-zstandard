import io
import struct
import unittest

import zstandard as zstd


class TestCompressor_compressobj(unittest.TestCase):
    def test_compressobj_empty(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        cobj = cctx.compressobj()
        self.assertEqual(cobj.compress(b""), b"")
        self.assertEqual(cobj.flush(), b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")

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
