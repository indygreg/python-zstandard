import struct
import unittest

import zstandard as zstd

from .common import (
    generate_samples,
    get_optimal_dict_size_heuristically,
)


@unittest.skipUnless(
    "multi_decompress_to_buffer" in zstd.backend_features,
    "multi_decompress_to_buffer feature not available",
)
class TestDecompressor_multi_decompress_to_buffer(unittest.TestCase):
    def test_invalid_inputs(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaises(TypeError):
            dctx.multi_decompress_to_buffer(True)

        with self.assertRaises(TypeError):
            dctx.multi_decompress_to_buffer((1, 2))

        with self.assertRaisesRegex(
            TypeError, "item 0 not a bytes like object"
        ):
            dctx.multi_decompress_to_buffer([u"foo"])

        with self.assertRaisesRegex(
            ValueError, "could not determine decompressed size of item 0"
        ):
            dctx.multi_decompress_to_buffer([b"foobarbaz"])

    def test_list_input(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(d) for d in original]

        dctx = zstd.ZstdDecompressor()

        result = dctx.multi_decompress_to_buffer(frames)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

        self.assertEqual(result[0].offset, 0)
        self.assertEqual(len(result[0]), 12)
        self.assertEqual(len(result[1]), 18)

    def test_list_input_frame_sizes(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6, b"baz" * 8]
        frames = [cctx.compress(d) for d in original]
        sizes = struct.pack("=" + "Q" * len(original), *map(len, original))

        dctx = zstd.ZstdDecompressor()

        result = dctx.multi_decompress_to_buffer(
            frames, decompressed_sizes=sizes
        )

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

    def test_buffer_with_segments_input(self):
        cctx = zstd.ZstdCompressor()

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(d) for d in original]

        dctx = zstd.ZstdDecompressor()

        segments = struct.pack(
            "=QQQQ", 0, len(frames[0]), len(frames[0]), len(frames[1])
        )
        b = zstd.BufferWithSegments(b"".join(frames), segments)

        result = dctx.multi_decompress_to_buffer(b)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result[0].offset, 0)
        self.assertEqual(len(result[0]), 12)
        self.assertEqual(len(result[1]), 18)

    def test_buffer_with_segments_sizes(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        original = [b"foo" * 4, b"bar" * 6, b"baz" * 8]
        frames = [cctx.compress(d) for d in original]
        sizes = struct.pack("=" + "Q" * len(original), *map(len, original))

        dctx = zstd.ZstdDecompressor()

        segments = struct.pack(
            "=QQQQQQ",
            0,
            len(frames[0]),
            len(frames[0]),
            len(frames[1]),
            len(frames[0]) + len(frames[1]),
            len(frames[2]),
        )
        b = zstd.BufferWithSegments(b"".join(frames), segments)

        result = dctx.multi_decompress_to_buffer(b, decompressed_sizes=sizes)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), sum(map(len, original)))

        for i, data in enumerate(original):
            self.assertEqual(result[i].tobytes(), data)

    def test_buffer_with_segments_collection_input(self):
        cctx = zstd.ZstdCompressor()

        original = [
            b"foo0" * 2,
            b"foo1" * 3,
            b"foo2" * 4,
            b"foo3" * 5,
            b"foo4" * 6,
        ]

        frames = cctx.multi_compress_to_buffer(original)

        # Check round trip.
        dctx = zstd.ZstdDecompressor()

        decompressed = dctx.multi_decompress_to_buffer(frames, threads=3)

        self.assertEqual(len(decompressed), len(original))

        for i, data in enumerate(original):
            self.assertEqual(data, decompressed[i].tobytes())

        # And a manual mode.
        b = b"".join([frames[0].tobytes(), frames[1].tobytes()])
        b1 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQ", 0, len(frames[0]), len(frames[0]), len(frames[1])
            ),
        )

        b = b"".join(
            [frames[2].tobytes(), frames[3].tobytes(), frames[4].tobytes()]
        )
        b2 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQQQ",
                0,
                len(frames[2]),
                len(frames[2]),
                len(frames[3]),
                len(frames[2]) + len(frames[3]),
                len(frames[4]),
            ),
        )

        c = zstd.BufferWithSegmentsCollection(b1, b2)

        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.multi_decompress_to_buffer(c)

        self.assertEqual(len(decompressed), 5)
        for i in range(5):
            self.assertEqual(decompressed[i].tobytes(), original[i])

    def test_dict(self):
        samples = generate_samples()
        optSize = get_optimal_dict_size_heuristically(samples)
        d = zstd.train_dictionary(optSize, samples, k=64, d=8)

        cctx = zstd.ZstdCompressor(dict_data=d, level=1)
        frames = [cctx.compress(s) for s in generate_samples()]

        dctx = zstd.ZstdDecompressor(dict_data=d)

        result = dctx.multi_decompress_to_buffer(frames)

        self.assertEqual([o.tobytes() for o in result], samples)

    def test_multiple_threads(self):
        cctx = zstd.ZstdCompressor()

        frames = []
        frames.extend(cctx.compress(b"x" * 64) for i in range(256))
        frames.extend(cctx.compress(b"y" * 64) for i in range(256))

        dctx = zstd.ZstdDecompressor()

        result = dctx.multi_decompress_to_buffer(frames, threads=-1)

        self.assertEqual(len(result), len(frames))
        self.assertEqual(result.size(), 2 * 64 * 256)
        self.assertEqual(result[0].tobytes(), b"x" * 64)
        self.assertEqual(result[256].tobytes(), b"y" * 64)

    def test_item_failure(self):
        cctx = zstd.ZstdCompressor()
        frames = [cctx.compress(b"x" * 128), cctx.compress(b"y" * 128)]

        frames[1] = frames[1][0:15] + b"extra" + frames[1][15:]

        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(
            zstd.ZstdError,
            "error decompressing item 1: ("
            "Corrupted block|"
            "Destination buffer is too small)",
        ):
            dctx.multi_decompress_to_buffer(frames)

        with self.assertRaisesRegex(
            zstd.ZstdError,
            "error decompressing item 1: ("
            "Corrupted block|"
            "Destination buffer is too small)",
        ):
            dctx.multi_decompress_to_buffer(frames, threads=2)
