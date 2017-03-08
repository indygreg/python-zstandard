import io
import os

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

from . common import (
    make_cffi,
    random_input_data,
)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestDecompressor_write_to_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      write_size=strategies.integers(min_value=1, max_value=8192),
                      input_sizes=strategies.streaming(
                          strategies.integers(min_value=1, max_value=4096)))
    def test_write_size_variance(self, original, level, write_size, input_sizes):
        input_sizes = iter(input_sizes)

        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        dctx = zstd.ZstdDecompressor()
        source = io.BytesIO(frame)
        dest = io.BytesIO()

        with dctx.write_to(dest, write_size=write_size) as decompressor:
            while True:
                chunk = source.read(next(input_sizes))
                if not chunk:
                    break

                decompressor.write(chunk)

        self.assertEqual(dest.getvalue(), original)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
class TestDecompressor_multi_decompress_to_buffer_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.lists(strategies.sampled_from(random_input_data()),
                                        min_size=1, max_size=1024),
                threads=strategies.integers(min_value=1, max_value=8),
                use_dict=strategies.booleans())
    def test_data_equivalence(self, original, threads, use_dict):
        kwargs = {}
        if use_dict:
            kwargs['dict_data'] = zstd.ZstdCompressionDict(original[0])

        cctx = zstd.ZstdCompressor(level=1, threads=-1,
                                    write_content_size=True,
                                    write_checksum=True,
                                    **kwargs)

        frames_buffer = cctx.multi_compress_to_buffer(original)

        dctx = zstd.ZstdDecompressor(**kwargs)

        result = dctx.multi_decompress_to_buffer(frames_buffer)

        self.assertEqual(len(result), len(original))
        for i, frame in enumerate(result):
            self.assertEqual(frame.tobytes(), original[i])

        frames_list = [f.tobytes() for f in frames_buffer]
        result = dctx.multi_decompress_to_buffer(frames_list)

        self.assertEqual(len(result), len(original))
        for i, frame in enumerate(result):
            self.assertEqual(frame.tobytes(), original[i])
