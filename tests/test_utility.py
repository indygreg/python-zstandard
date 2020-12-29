import unittest

import zstandard as zstd


class TestCompress(unittest.TestCase):
    def test_simple(self):
        frame = zstd.compress(b"foobar")

        fp = zstd.get_frame_parameters(frame)
        self.assertEqual(fp.content_size, 6)
        self.assertFalse(fp.has_checksum)

        zstd.compress(b"foobar" * 16384, level=7)


class TestDecompress(unittest.TestCase):
    def test_simple(self):
        source = b"foobar" * 8192
        frame = zstd.compress(source)
        self.assertEqual(zstd.decompress(frame), source)
