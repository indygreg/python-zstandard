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

    def test_write_checksum(self):
        cctx = zstd.ZstdCompressor(level=1)
        no_checksum = cctx.compress(b'foobar')
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        with_checksum = cctx.compress(b'foobar')

        self.assertEqual(len(with_checksum), len(no_checksum) + 4)

    def test_write_content_size(self):
        cctx = zstd.ZstdCompressor(level=1)
        no_size = cctx.compress(b'foobar' * 256)
        cctx = zstd.ZstdCompressor(level=1, write_content_size=True)
        with_size = cctx.compress(b'foobar' * 256)

        self.assertEqual(len(with_size), len(no_size) + 1)

    def test_no_dict_id(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(1024, samples)

        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        with_dict_id = cctx.compress(b'foobarfoobar')

        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_dict_id=False)
        no_dict_id = cctx.compress(b'foobarfoobar')

        self.assertEqual(len(with_dict_id), len(no_dict_id) + 4)

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
        self.assertEqual(int(r), 0)
        # Python 2.6 doesn't report bytes written :(
        self.assertIn(w, (0, 9))

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
        # Python 2.6 doesn't report bytes written :(
        self.assertIn(w, (0, 999))

    def test_write_checksum(self):
        source = io.BytesIO(b'foobar')
        no_checksum = io.BytesIO()

        cctx = zstd.ZstdCompressor(level=1)
        cctx.copy_stream(source, no_checksum)

        source.seek(0)
        with_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        cctx.copy_stream(source, with_checksum)

        self.assertEqual(len(with_checksum.getvalue()),
                         len(no_checksum.getvalue()) + 4)

    def test_write_content_size(self):
        source = io.BytesIO(b'foobar' * 256)
        no_size = io.BytesIO()

        cctx = zstd.ZstdCompressor(level=1)
        cctx.copy_stream(source, no_size)

        source.seek(0)
        with_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=True)
        cctx.copy_stream(source, with_size)

        # Source content size is unknown, so no content size written.
        self.assertEqual(len(with_size.getvalue()),
                         len(no_size.getvalue()))

        source.seek(0)
        with_size = io.BytesIO()
        cctx.copy_stream(source, with_size, size=len(source.getvalue()))

        # We specified source size, so content size header is present.
        self.assertEqual(len(with_size.getvalue()),
                         len(no_size.getvalue()) + 1)


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

    def test_write_checksum(self):
        no_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.write_to(no_checksum) as compressor:
            compressor.write(b'foobar')

        with_checksum = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_checksum=True)
        with cctx.write_to(with_checksum) as compressor:
            compressor.write(b'foobar')

        self.assertEqual(len(with_checksum.getvalue()),
                         len(no_checksum.getvalue()) + 4)

    def test_write_content_size(self):
        no_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.write_to(no_size) as compressor:
            compressor.write(b'foobar' * 256)

        with_size = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, write_content_size=True)
        with cctx.write_to(with_size) as compressor:
            compressor.write(b'foobar' * 256)

        # Source size is not known in streaming mode, so header not
        # written.
        self.assertEqual(len(with_size.getvalue()),
                         len(no_size.getvalue()))

        # Declaring size will write the header.
        with_size = io.BytesIO()
        with cctx.write_to(with_size, size=len(b'foobar' * 256)) as compressor:
            compressor.write(b'foobar' * 256)

        self.assertEqual(len(with_size.getvalue()),
                         len(no_size.getvalue()) + 1)

    def test_no_dict_id(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(1024, samples)

        with_dict_id = io.BytesIO()
        cctx = zstd.ZstdCompressor(level=1, dict_data=d)
        with cctx.write_to(with_dict_id) as compressor:
            compressor.write(b'foobarfoobar')

        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_dict_id=False)
        no_dict_id = io.BytesIO()
        with cctx.write_to(no_dict_id) as compressor:
            compressor.write(b'foobarfoobar')

        self.assertEqual(len(with_dict_id.getvalue()),
                         len(no_dict_id.getvalue()) + 4)
