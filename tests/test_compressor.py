import unittest

import zstandard as zstd


class TestCompressor(unittest.TestCase):
    def test_level_bounds(self):
        with self.assertRaises(ValueError):
            zstd.ZstdCompressor(level=23)

    def test_memory_size(self):
        cctx = zstd.ZstdCompressor(level=1)
        self.assertGreater(cctx.memory_size(), 100)
