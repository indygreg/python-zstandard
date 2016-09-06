import hashlib
import io
import struct

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import zstd


class TestCompressor(unittest.TestCase):
    def test_level_bounds(self):
        with self.assertRaises(ValueError):
            zstd.ZstdCompressor(level=0)

        with self.assertRaises(ValueError):
            zstd.ZstdCompressor(level=23)


class TestCompressor_compress(unittest.TestCase):
    def test_compress_empty(self):
        cctx = zstd.ZstdCompressor(level=1)
        cctx.compress(b'')

        cctx = zstd.ZstdCompressor(level=22)
        cctx.compress(b'')

    def test_compress_empty(self):
        cctx = zstd.ZstdCompressor(level=1)
        self.assertEqual(cctx.compress(b''),
                         b'\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00')

    def test_compress_large(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct('>B').pack(i) * 16384)

        cctx = zstd.ZstdCompressor(level=3)
        result = cctx.compress(b''.join(chunks))
        self.assertEqual(len(result), 999)
        self.assertEqual(result[0:4], b'\x28\xb5\x2f\xfd')


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

        cctx = zstd.ZstdCompressor(level=1)
        r, w = cctx.copy_stream(source, dest)
        self.assertEqual(r, 0)
        self.assertEqual(w, 9)

        self.assertEqual(dest.getvalue(),
                         b'\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00')

    def test_large_data(self):
        source = io.BytesIO()
        for i in range(255):
            source.write(struct.Struct('>B').pack(i) * 16384)
        source.seek(0)

        dest = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        r, w = cctx.copy_stream(source, dest)

        self.assertEqual(r, 255 * 16384)
        self.assertEqual(w, 999)


def compress(data, level):
    buffer = io.BytesIO()
    cctx = zstd.ZstdCompressor(level=level)
    with cctx.write_to(buffer) as compressor:
        compressor.write(data)
    return buffer.getvalue()


class TestCompressor_write_to(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(compress(b'', 1),
                         b'\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00')

    def test_multiple_compress(self):
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=5)
        with cctx.write_to(buffer) as compressor:
            compressor.write(b'foo')
            compressor.write(b'bar')
            compressor.write(b'x' * 8192)

        result = buffer.getvalue()
        self.assertEqual(result,
                         b'\x28\xb5\x2f\xfd\x00\x50\x75\x00\x00\x38\x66\x6f'
                         b'\x6f\x62\x61\x72\x78\x01\x00\xfc\xdf\x03\x23')

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(8192, samples)

        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=9, dict_data=d)
        with cctx.write_to(buffer) as compressor:
            compressor.write(b'foo')
            compressor.write(b'bar')
            compressor.write(b'foo' * 16384)

        compressed = buffer.getvalue()
        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, '1c5bcd25181bcd8c1a73ea8773323e0056129f92')

    def test_compression_params(self):
        params = zstd.CompressionParameters(20, 6, 12, 5, 4, 10, zstd.STRATEGY_FAST)

        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(compression_params=params)
        with cctx.write_to(buffer) as compressor:
            compressor.write(b'foo')
            compressor.write(b'bar')
            compressor.write(b'foobar' * 16384)

        compressed = buffer.getvalue()
        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, '1ae31f270ed7de14235221a604b31ecd517ebd99')

