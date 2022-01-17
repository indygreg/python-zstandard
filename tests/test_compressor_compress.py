import struct
import unittest

import zstandard as zstd


def multithreaded_chunk_size(level, source_size=0):
    params = zstd.ZstdCompressionParameters.from_level(
        level, source_size=source_size
    )

    return 1 << (params.window_log + 2)


class TestCompressor_compress(unittest.TestCase):
    def test_compress_empty(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        result = cctx.compress(b"")
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")
        params = zstd.get_frame_parameters(result)
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
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
        self.assertEqual(with_params.dict_id, 1123828263)

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
            b"\x28\xb5\x2f\xfd\x23\x27\x42\xfc\x42\x03\x19\x00\x00"
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

    def test_explicit_default_params(self):
        cctx = zstd.ZstdCompressor(
            level=3,
            dict_data=None,
            compression_params=None,
            write_checksum=None,
            write_content_size=None,
            write_dict_id=None,
            threads=0,
        )
        result = cctx.compress(b"")
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x20\x00\x01\x00\x00")

    def test_compression_params_with_other_params(self):
        params = zstd.ZstdCompressionParameters.from_level(3)
        cctx = zstd.ZstdCompressor(
            level=3,
            dict_data=None,
            compression_params=params,
            write_checksum=None,
            write_content_size=None,
            write_dict_id=None,
            threads=0,
        )
        result = cctx.compress(b"")
        self.assertEqual(result, b"\x28\xb5\x2f\xfd\x20\x00\x01\x00\x00")

        with self.assertRaises(ValueError):
            cctx = zstd.ZstdCompressor(
                level=3,
                dict_data=None,
                compression_params=params,
                write_checksum=False,
                write_content_size=None,
                write_dict_id=None,
                threads=0,
            )

        with self.assertRaises(ValueError):
            cctx = zstd.ZstdCompressor(
                level=3,
                dict_data=None,
                compression_params=params,
                write_checksum=None,
                write_content_size=True,
                write_dict_id=None,
                threads=0,
            )

        with self.assertRaises(ValueError):
            cctx = zstd.ZstdCompressor(
                level=3,
                dict_data=None,
                compression_params=params,
                write_checksum=None,
                write_content_size=None,
                write_dict_id=True,
                threads=0,
            )

        with self.assertRaises(ValueError):
            cctx = zstd.ZstdCompressor(
                level=3,
                dict_data=None,
                compression_params=params,
                write_checksum=None,
                write_content_size=None,
                write_dict_id=True,
                threads=2,
            )
