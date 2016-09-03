import io

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import hypothesis
    import hypothesis.strategies as strategies
except ImportError:
    raise unittest.SkipTest('hypothesis not available')

import zstd


compression_levels = strategies.integers(min_value=1, max_value=22)


class TestRoundTrip(unittest.TestCase):
    @hypothesis.given(strategies.binary(), compression_levels)
    def test_compress_decompresswriter(self, data, level):
        """Random data from compress() roundtrips via decompresswriter."""
        compressed = zstd.compress(data, level)

        buffer = io.BytesIO()
        with zstd.decompresswriter(buffer) as f:
            f.decompress(compressed)

        self.assertEqual(buffer.getvalue(), data)

    @hypothesis.given(strategies.binary(), compression_levels)
    def test_compresswriter_decompresswriter(self, data, level):
        """Random data from compresswriter roundtrips via decompresswriter."""
        compress_buffer = io.BytesIO()
        decompressed_buffer = io.BytesIO()

        with zstd.compresswriter(compress_buffer, level) as compressor:
            compressor.compress(data)

        with zstd.decompresswriter(decompressed_buffer) as decompressor:
            decompressor.decompress(compress_buffer.getvalue())

        self.assertEqual(decompressed_buffer.getvalue(), data)

    @hypothesis.given(strategies.binary(average_size=1048576))
    @hypothesis.settings(perform_health_check=False)
    def test_compresswriter_decompresswriter_larger(self, data):
        compress_buffer = io.BytesIO()
        decompressed_buffer = io.BytesIO()

        with zstd.compresswriter(compress_buffer, 5) as compressor:
            compressor.compress(data)

        with zstd.decompresswriter(decompressed_buffer) as decompressor:
            decompressor.decompress(compress_buffer.getvalue())

        self.assertEqual(decompressed_buffer.getvalue(), data)
