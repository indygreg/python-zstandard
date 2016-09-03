from __future__ import unicode_literals

import hashlib
import io
import unittest

import zstd


def compress(data, level):
    buffer = io.BytesIO()
    with zstd.compresswriter(buffer, compression_level=level) as f:
        f.compress(data)
    return buffer.getvalue()


class TestCompressWriter(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(compress(b'', 1),
                         b'\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00')

    def test_multiple_compress(self):
        buffer = io.BytesIO()
        with zstd.compresswriter(buffer, compression_level=5) as compressor:
            compressor.compress(b'foo')
            compressor.compress(b'bar')
            compressor.compress(b'x' * 8192)

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
        with zstd.compresswriter(buffer, compression_level=9, dict_data=d) as compressor:
            compressor.compress(b'foo')
            compressor.compress(b'bar')
            compressor.compress(b'foo' * 16384)

        compressed = buffer.getvalue()
        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, '1c5bcd25181bcd8c1a73ea8773323e0056129f92')

    def test_compression_params(self):
        params = zstd.CompressionParameters(20, 6, 12, 5, 4, 10, zstd.STRATEGY_FAST)

        buffer = io.BytesIO()
        with zstd.compresswriter(buffer, compression_params=params) as compressor:
            compressor.compress(b'foo')
            compressor.compress(b'bar')
            compressor.compress(b'foobar' * 16384)

        compressed = buffer.getvalue()
        h = hashlib.sha1(compressed).hexdigest()
        self.assertEqual(h, '1ae31f270ed7de14235221a604b31ecd517ebd99')

