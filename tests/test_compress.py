from __future__ import unicode_literals

import struct
import unittest

import zstd

class TestCompress(unittest.TestCase):
    def test_compress_bounds(self):
        with self.assertRaises(ValueError):
            zstd.compress(b'', 0)
        with self.assertRaises(ValueError):
            zstd.compress(b'', 23)

        zstd.compress(b'', 1)
        zstd.compress(b'', 22)

    def test_compress_empty(self):
        self.assertEqual(zstd.compress(b'', 1),
                         b'\x28\xb5\x2f\xfd\x00\x48\x01\x00\x00')

    def test_compress_large(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct('>B').pack(i) * 16384)

        result = zstd.compress(b''.join(chunks))
        self.assertEqual(len(result), 1003)
        self.assertEqual(result[0:4], b'\x28\xb5\x2f\xfd')
