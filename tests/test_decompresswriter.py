from __future__ import unicode_literals

import io
import struct
import unittest

import zstd


def decompress(data):
    buffer = io.BytesIO()
    with zstd.decompresswriter(buffer) as f:
        f.decompress(data)
    return buffer.getvalue()


class TestDecompressWriter(unittest.TestCase):
    def test_empty_roundtrip(self):
        empty = zstd.compress(b'')
        self.assertEqual(decompress(empty), b'')

    def test_large_roundtrip(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct('>B').pack(i) * 16384)

        orig = b''.join(chunks)
        compressed = zstd.compress(orig)
        decompressed = decompress(compressed)
        self.assertEqual(decompressed, orig)

    def test_multiple_calls(self):
        chunks = []
        for i in range(255):
            for j in range(255):
                chunks.append(struct.Struct('>B').pack(j) * i)

        orig = b''.join(chunks)
        compressed = zstd.compress(orig)

        buffer = io.BytesIO()
        with zstd.decompresswriter(buffer) as f:
            pos = 0
            while pos < len(compressed):
                pos2 = pos + 8192
                f.decompress(compressed[pos:pos2])
                pos += 8192
        self.assertEqual(buffer.getvalue(), orig)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(8192, samples)

        orig = b'foobar' * 16384
        buffer = io.BytesIO()
        with zstd.compresswriter(buffer, dict_data=d) as compressor:
            compressor.compress(orig)

        compressed = buffer.getvalue()
        buffer = io.BytesIO()

        with zstd.decompresswriter(buffer, dict_data=d) as decompressor:
            decompressor.decompress(compressed)

        self.assertEqual(buffer.getvalue(), orig)
