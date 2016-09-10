import io
import struct

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import zstd


class TestDecompressor_copy_stream(unittest.TestCase):
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
        self.assertEqual(dest.getvalue(), b'')

    def test_large_data(self):
        source = io.BytesIO()
        for i in range(255):
            source.write(struct.Struct('>B').pack(i) * 16384)
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


def decompress_via_writer(data):
    buffer = io.BytesIO()
    dctx = zstd.ZstdDecompressor()
    with dctx.write_to(buffer) as decompressor:
        decompressor.write(data)
    return buffer.getvalue()


class TestDecompressor_write_to(unittest.TestCase):
    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor()
        empty = cctx.compress(b'')
        self.assertEqual(decompress_via_writer(empty), b'')

    def test_large_roundtrip(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct('>B').pack(i) * 16384)
        orig = b''.join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        self.assertEqual(decompress_via_writer(compressed), orig)

    def test_multiple_calls(self):
        chunks = []
        for i in range(255):
            for j in range(255):
                chunks.append(struct.Struct('>B').pack(j) * i)

        orig = b''.join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        buffer = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.write_to(buffer) as decompressor:
            pos = 0
            while pos < len(compressed):
                pos2 = pos + 8192
                decompressor.write(compressed[pos:pos2])
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
        cctx = zstd.ZstdCompressor(dict_data=d)
        with cctx.write_to(buffer) as compressor:
            compressor.write(orig)

        compressed = buffer.getvalue()
        buffer = io.BytesIO()

        dctx = zstd.ZstdDecompressor(dict_data=d)
        with dctx.write_to(buffer) as decompressor:
            decompressor.write(compressed)

        self.assertEqual(buffer.getvalue(), orig)

    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()
        buffer = io.BytesIO()
        with dctx.write_to(buffer) as decompressor:
            size = decompressor.memory_size()

        self.assertGreater(size, 100000)
