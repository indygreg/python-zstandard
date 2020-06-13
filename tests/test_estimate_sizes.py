import zstandard as zstd

from .common import TestCase


class TestSizes(TestCase):
    def test_decompression_size(self):
        size = zstd.estimate_decompression_context_size()
        self.assertGreater(size, 100000)
