import io
import os
import unittest

try:
    import hypothesis
    import hypothesis.strategies as strategies
except ImportError:
    raise unittest.SkipTest("hypothesis not available")

import zstandard as zstd

from .common import (
    make_cffi,
    NonClosingBytesIO,
    random_input_data,
    TestCase,
)


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
@make_cffi
class TestDecompressor_stream_reader_fuzzing(TestCase):
    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_sizes=strategies.data(),
    )
    def test_stream_source_read_variance(
        self, original, level, streaming, source_read_size, read_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            source.seek(0)
        else:
            frame = cctx.compress(original)
            source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()

        chunks = []
        with dctx.stream_reader(source, read_size=source_read_size) as reader:
            while True:
                read_size = read_sizes.draw(strategies.integers(-1, 131072))
                chunk = reader.read(read_size)
                if not chunk and read_size:
                    break

                chunks.append(chunk)

        self.assertEqual(b"".join(chunks), original)

    # Similar to above except we have a constant read() size.
    @hypothesis.settings(
        suppress_health_check=[hypothesis.HealthCheck.large_base_example]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_size=strategies.integers(-1, 131072),
    )
    def test_stream_source_read_size(
        self, original, level, streaming, source_read_size, read_size
    ):
        if read_size == 0:
            read_size = 1

        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            source.seek(0)
        else:
            frame = cctx.compress(original)
            source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()

        chunks = []
        reader = dctx.stream_reader(source, read_size=source_read_size)
        while True:
            chunk = reader.read(read_size)
            if not chunk and read_size:
                break

            chunks.append(chunk)

        self.assertEqual(b"".join(chunks), original)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_sizes=strategies.data(),
    )
    def test_buffer_source_read_variance(
        self, original, level, streaming, source_read_size, read_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            frame = source.getvalue()
        else:
            frame = cctx.compress(original)

        dctx = zstd.ZstdDecompressor()
        chunks = []

        with dctx.stream_reader(frame, read_size=source_read_size) as reader:
            while True:
                read_size = read_sizes.draw(strategies.integers(-1, 131072))
                chunk = reader.read(read_size)
                if not chunk and read_size:
                    break

                chunks.append(chunk)

        self.assertEqual(b"".join(chunks), original)

    # Similar to above except we have a constant read() size.
    @hypothesis.settings(
        suppress_health_check=[hypothesis.HealthCheck.large_base_example]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_size=strategies.integers(-1, 131072),
    )
    def test_buffer_source_constant_read_size(
        self, original, level, streaming, source_read_size, read_size
    ):
        if read_size == 0:
            read_size = -1

        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            frame = source.getvalue()
        else:
            frame = cctx.compress(original)

        dctx = zstd.ZstdDecompressor()
        chunks = []

        reader = dctx.stream_reader(frame, read_size=source_read_size)
        while True:
            chunk = reader.read(read_size)
            if not chunk and read_size:
                break

            chunks.append(chunk)

        self.assertEqual(b"".join(chunks), original)

    @hypothesis.settings(
        suppress_health_check=[hypothesis.HealthCheck.large_base_example]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
    )
    def test_stream_source_readall(
        self, original, level, streaming, source_read_size
    ):
        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            source.seek(0)
        else:
            frame = cctx.compress(original)
            source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()

        data = dctx.stream_reader(source, read_size=source_read_size).readall()
        self.assertEqual(data, original)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_sizes=strategies.data(),
    )
    def test_stream_source_read1_variance(
        self, original, level, streaming, source_read_size, read_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            source.seek(0)
        else:
            frame = cctx.compress(original)
            source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()

        chunks = []
        with dctx.stream_reader(source, read_size=source_read_size) as reader:
            while True:
                read_size = read_sizes.draw(strategies.integers(-1, 131072))
                chunk = reader.read1(read_size)
                if not chunk and read_size:
                    break

                chunks.append(chunk)

        self.assertEqual(b"".join(chunks), original)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        streaming=strategies.booleans(),
        source_read_size=strategies.integers(1, 1048576),
        read_sizes=strategies.data(),
    )
    def test_stream_source_readinto1_variance(
        self, original, level, streaming, source_read_size, read_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)

        if streaming:
            source = io.BytesIO()
            writer = cctx.stream_writer(source)
            writer.write(original)
            writer.flush(zstd.FLUSH_FRAME)
            source.seek(0)
        else:
            frame = cctx.compress(original)
            source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()

        chunks = []
        with dctx.stream_reader(source, read_size=source_read_size) as reader:
            while True:
                read_size = read_sizes.draw(strategies.integers(1, 131072))
                b = bytearray(read_size)
                count = reader.readinto1(b)

                if not count:
                    break

                chunks.append(bytes(b[0:count]))

        self.assertEqual(b"".join(chunks), original)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        source_read_size=strategies.integers(1, 1048576),
        seek_amounts=strategies.data(),
        read_sizes=strategies.data(),
    )
    def test_relative_seeks(
        self, original, level, source_read_size, seek_amounts, read_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        dctx = zstd.ZstdDecompressor()

        with dctx.stream_reader(frame, read_size=source_read_size) as reader:
            while True:
                amount = seek_amounts.draw(strategies.integers(0, 16384))
                reader.seek(amount, os.SEEK_CUR)

                offset = reader.tell()
                read_amount = read_sizes.draw(strategies.integers(1, 16384))
                chunk = reader.read(read_amount)

                if not chunk:
                    break

                self.assertEqual(original[offset : offset + len(chunk)], chunk)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        originals=strategies.data(),
        frame_count=strategies.integers(min_value=2, max_value=10),
        level=strategies.integers(min_value=1, max_value=5),
        source_read_size=strategies.integers(1, 1048576),
        read_sizes=strategies.data(),
    )
    def test_multiple_frames(
        self, originals, frame_count, level, source_read_size, read_sizes
    ):

        cctx = zstd.ZstdCompressor(level=level)
        source = io.BytesIO()
        buffer = io.BytesIO()
        writer = cctx.stream_writer(buffer)

        for i in range(frame_count):
            data = originals.draw(strategies.sampled_from(random_input_data()))
            source.write(data)
            writer.write(data)
            writer.flush(zstd.FLUSH_FRAME)

        dctx = zstd.ZstdDecompressor()
        buffer.seek(0)
        reader = dctx.stream_reader(
            buffer, read_size=source_read_size, read_across_frames=True
        )

        chunks = []

        while True:
            read_amount = read_sizes.draw(strategies.integers(-1, 16384))
            chunk = reader.read(read_amount)

            if not chunk and read_amount:
                break

            chunks.append(chunk)

        self.assertEqual(source.getvalue(), b"".join(chunks))


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
@make_cffi
class TestDecompressor_stream_writer_fuzzing(TestCase):
    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        write_size=strategies.integers(min_value=1, max_value=8192),
        input_sizes=strategies.data(),
    )
    def test_write_size_variance(
        self, original, level, write_size, input_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        dctx = zstd.ZstdDecompressor()
        source = io.BytesIO(frame)
        dest = NonClosingBytesIO()

        with dctx.stream_writer(dest, write_size=write_size) as decompressor:
            while True:
                input_size = input_sizes.draw(strategies.integers(1, 4096))
                chunk = source.read(input_size)
                if not chunk:
                    break

                decompressor.write(chunk)

        self.assertEqual(dest.getvalue(), original)


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
@make_cffi
class TestDecompressor_copy_stream_fuzzing(TestCase):
    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        read_size=strategies.integers(min_value=1, max_value=8192),
        write_size=strategies.integers(min_value=1, max_value=8192),
    )
    def test_read_write_size_variance(
        self, original, level, read_size, write_size
    ):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        source = io.BytesIO(frame)
        dest = io.BytesIO()

        dctx = zstd.ZstdDecompressor()
        dctx.copy_stream(
            source, dest, read_size=read_size, write_size=write_size
        )

        self.assertEqual(dest.getvalue(), original)


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
@make_cffi
class TestDecompressor_decompressobj_fuzzing(TestCase):
    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        chunk_sizes=strategies.data(),
    )
    def test_random_input_sizes(self, original, level, chunk_sizes):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()

        chunks = []
        while True:
            chunk_size = chunk_sizes.draw(strategies.integers(1, 4096))
            chunk = source.read(chunk_size)
            if not chunk:
                break

            chunks.append(dobj.decompress(chunk))

        self.assertEqual(b"".join(chunks), original)

    @hypothesis.settings(
        suppress_health_check=[
            hypothesis.HealthCheck.large_base_example,
            hypothesis.HealthCheck.too_slow,
        ]
    )
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        write_size=strategies.integers(
            min_value=1,
            max_value=4 * zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE,
        ),
        chunk_sizes=strategies.data(),
    )
    def test_random_output_sizes(
        self, original, level, write_size, chunk_sizes
    ):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj(write_size=write_size)

        chunks = []
        while True:
            chunk_size = chunk_sizes.draw(strategies.integers(1, 4096))
            chunk = source.read(chunk_size)
            if not chunk:
                break

            chunks.append(dobj.decompress(chunk))

        self.assertEqual(b"".join(chunks), original)


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
@make_cffi
class TestDecompressor_read_to_iter_fuzzing(TestCase):
    @hypothesis.given(
        original=strategies.sampled_from(random_input_data()),
        level=strategies.integers(min_value=1, max_value=5),
        read_size=strategies.integers(min_value=1, max_value=4096),
        write_size=strategies.integers(min_value=1, max_value=4096),
    )
    def test_read_write_size_variance(
        self, original, level, read_size, write_size
    ):
        cctx = zstd.ZstdCompressor(level=level)
        frame = cctx.compress(original)

        source = io.BytesIO(frame)

        dctx = zstd.ZstdDecompressor()
        chunks = list(
            dctx.read_to_iter(
                source, read_size=read_size, write_size=write_size
            )
        )

        self.assertEqual(b"".join(chunks), original)


@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
class TestDecompressor_multi_decompress_to_buffer_fuzzing(TestCase):
    @hypothesis.given(
        original=strategies.lists(
            strategies.sampled_from(random_input_data()),
            min_size=1,
            max_size=1024,
        ),
        threads=strategies.integers(min_value=1, max_value=8),
        use_dict=strategies.booleans(),
    )
    def test_data_equivalence(self, original, threads, use_dict):
        kwargs = {}
        if use_dict:
            kwargs["dict_data"] = zstd.ZstdCompressionDict(original[0])

        cctx = zstd.ZstdCompressor(
            level=1, write_content_size=True, write_checksum=True, **kwargs
        )

        if not hasattr(cctx, "multi_compress_to_buffer"):
            self.skipTest("multi_compress_to_buffer not available")

        frames_buffer = cctx.multi_compress_to_buffer(original, threads=-1)

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
