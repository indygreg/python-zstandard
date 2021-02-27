import io
import os
import random
import struct
import unittest

import zstandard as zstd

from .common import (
    CustomBytesIO,
)


class TestDecompressor_read_to_iter(unittest.TestCase):
    def test_type_validation(self):
        dctx = zstd.ZstdDecompressor()

        # Object with read() works.
        dctx.read_to_iter(io.BytesIO())

        # Buffer protocol works.
        dctx.read_to_iter(b"foobar")

        with self.assertRaisesRegex(
            ValueError, "must pass an object with a read"
        ):
            b"".join(dctx.read_to_iter(True))

    def test_empty_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO()
        it = dctx.read_to_iter(source)
        # TODO this is arguably wrong. Should get an error about missing frame foo.
        with self.assertRaises(StopIteration):
            next(it)

        it = dctx.read_to_iter(b"")
        with self.assertRaises(StopIteration):
            next(it)

    def test_invalid_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO(b"foobar")
        it = dctx.read_to_iter(source)
        with self.assertRaisesRegex(zstd.ZstdError, "Unknown frame descriptor"):
            next(it)

        it = dctx.read_to_iter(b"foobar")
        with self.assertRaisesRegex(zstd.ZstdError, "Unknown frame descriptor"):
            next(it)

    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        empty = cctx.compress(b"")

        source = io.BytesIO(empty)
        source.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(source)

        # No chunks should be emitted since there is no data.
        with self.assertRaises(StopIteration):
            next(it)

        # Again for good measure.
        with self.assertRaises(StopIteration):
            next(it)

    def test_skip_bytes_too_large(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(
            ValueError, "skip_bytes must be smaller than read_size"
        ):
            b"".join(dctx.read_to_iter(b"", skip_bytes=1, read_size=1))

        with self.assertRaisesRegex(
            ValueError, "skip_bytes larger than first input chunk"
        ):
            b"".join(dctx.read_to_iter(b"foobar", skip_bytes=10))

    def test_skip_bytes(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b"foobar")

        dctx = zstd.ZstdDecompressor()
        output = b"".join(dctx.read_to_iter(b"hdr" + compressed, skip_bytes=3))
        self.assertEqual(output, b"foobar")

    def test_large_output(self):
        source = io.BytesIO()
        source.write(b"f" * zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE)
        source.write(b"o")
        source.seek(0)

        cctx = zstd.ZstdCompressor(level=1)
        compressed = io.BytesIO(cctx.compress(source.getvalue()))
        compressed.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(decompressed, source.getvalue())

        # And again with buffer protocol.
        it = dctx.read_to_iter(compressed.getvalue())
        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(decompressed, source.getvalue())

    @unittest.skipUnless(
        "ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set"
    )
    def test_large_input(self):
        bytes = list(struct.Struct(">B").pack(i) for i in range(256))
        compressed = io.BytesIO()
        input_size = 0
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.stream_writer(compressed, closefd=False) as compressor:
            while True:
                compressor.write(random.choice(bytes))
                input_size += 1

                have_compressed = (
                    len(compressed.getvalue())
                    > zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE
                )
                have_raw = (
                    input_size > zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE * 2
                )
                if have_compressed and have_raw:
                    break

        compressed = io.BytesIO(compressed.getvalue())
        self.assertGreater(
            len(compressed.getvalue()),
            zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE,
        )

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_to_iter(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(len(decompressed), input_size)

        # And again with buffer protocol.
        it = dctx.read_to_iter(compressed.getvalue())

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b"".join(chunks)
        self.assertEqual(len(decompressed), input_size)

    def test_interesting(self):
        # Found this edge case via fuzzing.
        cctx = zstd.ZstdCompressor(level=1)

        source = io.BytesIO()

        compressed = io.BytesIO()
        with cctx.stream_writer(compressed, closefd=False) as compressor:
            for i in range(256):
                chunk = b"\0" * 1024
                compressor.write(chunk)
                source.write(chunk)

        dctx = zstd.ZstdDecompressor()

        simple = dctx.decompress(
            compressed.getvalue(), max_output_size=len(source.getvalue())
        )
        self.assertEqual(simple, source.getvalue())

        compressed = io.BytesIO(compressed.getvalue())
        streamed = b"".join(dctx.read_to_iter(compressed))
        self.assertEqual(streamed, source.getvalue())

    def test_read_write_size(self):
        source = CustomBytesIO(zstd.ZstdCompressor().compress(b"foobarfoobar"))
        dctx = zstd.ZstdDecompressor()
        for chunk in dctx.read_to_iter(source, read_size=1, write_size=1):
            self.assertEqual(len(chunk), 1)

        self.assertEqual(source._read_count, len(source.getvalue()))

    def test_magic_less(self):
        params = zstd.ZstdCompressionParameters.from_level(
            1, format=zstd.FORMAT_ZSTD1_MAGICLESS
        )
        cctx = zstd.ZstdCompressor(compression_params=params)
        frame = cctx.compress(b"foobar")

        self.assertNotEqual(frame[0:4], b"\x28\xb5\x2f\xfd")

        dctx = zstd.ZstdDecompressor()
        with self.assertRaisesRegex(
            zstd.ZstdError, "error determining content size from frame header"
        ):
            dctx.decompress(frame)

        dctx = zstd.ZstdDecompressor(format=zstd.FORMAT_ZSTD1_MAGICLESS)
        res = b"".join(dctx.read_to_iter(frame))
        self.assertEqual(res, b"foobar")
