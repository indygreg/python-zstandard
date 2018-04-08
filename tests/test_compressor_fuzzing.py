import io
import os
import unittest

try:
    import hypothesis
    import hypothesis.strategies as strategies
except ImportError:
    raise unittest.SkipTest('hypothesis not available')

import zstandard as zstd

from . common import (
    make_cffi,
    random_input_data,
)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestCompressor_stream_reader_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      source_read_size=strategies.integers(1, 16384),
                      read_sizes=strategies.data())
    def test_stream_source_read_variance(self, original, level, source_read_size,
                                         read_sizes):
        refctx = zstd.ZstdCompressor(level=level)
        ref_frame = refctx.compress(original)

        cctx = zstd.ZstdCompressor(level=level)
        with cctx.stream_reader(io.BytesIO(original), size=len(original),
                                read_size=source_read_size) as reader:
            chunks = []
            while True:
                read_size = read_sizes.draw(strategies.integers(1, 16384))
                chunk = reader.read(read_size)

                if not chunk:
                    break
                chunks.append(chunk)

        self.assertEqual(b''.join(chunks), ref_frame)

    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      source_read_size=strategies.integers(1, 16384),
                      read_sizes=strategies.data())
    def test_buffer_source_read_variance(self, original, level, source_read_size,
                                         read_sizes):

        refctx = zstd.ZstdCompressor(level=level)
        ref_frame = refctx.compress(original)

        cctx = zstd.ZstdCompressor(level=level)
        with cctx.stream_reader(original, size=len(original),
                                read_size=source_read_size) as reader:
            chunks = []
            while True:
                read_size = read_sizes.draw(strategies.integers(1, 16384))
                chunk = reader.read(read_size)
                if not chunk:
                    break
                chunks.append(chunk)

        self.assertEqual(b''.join(chunks), ref_frame)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestCompressor_stream_writer_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                        level=strategies.integers(min_value=1, max_value=5),
                        write_size=strategies.integers(min_value=1, max_value=1048576))
    def test_write_size_variance(self, original, level, write_size):
        refctx = zstd.ZstdCompressor(level=level)
        ref_frame = refctx.compress(original)

        cctx = zstd.ZstdCompressor(level=level)
        b = io.BytesIO()
        with cctx.stream_writer(b, size=len(original), write_size=write_size) as compressor:
            compressor.write(original)

        self.assertEqual(b.getvalue(), ref_frame)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestCompressor_copy_stream_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      read_size=strategies.integers(min_value=1, max_value=1048576),
                      write_size=strategies.integers(min_value=1, max_value=1048576))
    def test_read_write_size_variance(self, original, level, read_size, write_size):
        refctx = zstd.ZstdCompressor(level=level)
        ref_frame = refctx.compress(original)

        cctx = zstd.ZstdCompressor(level=level)
        source = io.BytesIO(original)
        dest = io.BytesIO()

        cctx.copy_stream(source, dest, size=len(original), read_size=read_size,
                         write_size=write_size)

        self.assertEqual(dest.getvalue(), ref_frame)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestCompressor_compressobj_fuzzing(unittest.TestCase):
    @hypothesis.settings(
        suppress_health_check=[hypothesis.HealthCheck.large_base_example])
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      chunk_sizes=strategies.data())
    def test_random_input_sizes(self, original, level, chunk_sizes):
        refctx = zstd.ZstdCompressor(level=level)
        ref_frame = refctx.compress(original)

        cctx = zstd.ZstdCompressor(level=level)
        cobj = cctx.compressobj(size=len(original))

        chunks = []
        i = 0
        while True:
            chunk_size = chunk_sizes.draw(strategies.integers(1, 4096))
            source = original[i:i + chunk_size]
            if not source:
                break

            chunks.append(cobj.compress(source))
            i += chunk_size

        chunks.append(cobj.flush())

        self.assertEqual(b''.join(chunks), ref_frame)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
@make_cffi
class TestCompressor_read_to_iter_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.sampled_from(random_input_data()),
                      level=strategies.integers(min_value=1, max_value=5),
                      read_size=strategies.integers(min_value=1, max_value=4096),
                      write_size=strategies.integers(min_value=1, max_value=4096))
    def test_read_write_size_variance(self, original, level, read_size, write_size):
        refcctx = zstd.ZstdCompressor(level=level)
        ref_frame = refcctx.compress(original)

        source = io.BytesIO(original)

        cctx = zstd.ZstdCompressor(level=level)
        chunks = list(cctx.read_to_iter(source, size=len(original),
                                        read_size=read_size,
                                        write_size=write_size))

        self.assertEqual(b''.join(chunks), ref_frame)


@unittest.skipUnless('ZSTD_SLOW_TESTS' in os.environ, 'ZSTD_SLOW_TESTS not set')
class TestCompressor_multi_compress_to_buffer_fuzzing(unittest.TestCase):
    @hypothesis.given(original=strategies.lists(strategies.sampled_from(random_input_data()),
                                                min_size=1, max_size=1024),
                        threads=strategies.integers(min_value=1, max_value=8),
                        use_dict=strategies.booleans())
    def test_data_equivalence(self, original, threads, use_dict):
        kwargs = {}

        # Use a content dictionary because it is cheap to create.
        if use_dict:
            kwargs['dict_data'] = zstd.ZstdCompressionDict(original[0])

        cctx = zstd.ZstdCompressor(level=1,
                                   write_checksum=True,
                                   **kwargs)

        result = cctx.multi_compress_to_buffer(original, threads=-1)

        self.assertEqual(len(result), len(original))

        # The frame produced via the batch APIs may not be bit identical to that
        # produced by compress() because compression parameters are adjusted
        # from the first input in batch mode. So the only thing we can do is
        # verify the decompressed data matches the input.
        dctx = zstd.ZstdDecompressor(**kwargs)

        for i, frame in enumerate(result):
            self.assertEqual(dctx.decompress(frame), original[i])
