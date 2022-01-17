import unittest

import zstandard as zstd


class TestSizes(unittest.TestCase):
    def test_decompression_size(self):
        size = zstd.estimate_decompression_context_size()
        self.assertGreater(size, 90000)
