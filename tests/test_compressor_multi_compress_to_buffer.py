import struct
import unittest

import zstandard as zstd


@unittest.skipUnless(
    "multi_compress_to_buffer" in zstd.backend_features,
    "multi_compress_to_buffer feature not available",
)
class TestCompressor_multi_compress_to_buffer(unittest.TestCase):
    def test_invalid_inputs(self):
        cctx = zstd.ZstdCompressor()

        with self.assertRaises(TypeError):
            cctx.multi_compress_to_buffer(True)

        with self.assertRaises(TypeError):
            cctx.multi_compress_to_buffer((1, 2))

        with self.assertRaisesRegex(
            TypeError, "item 0 not a bytes like object"
        ):
            cctx.multi_compress_to_buffer([u"foo"])

    def test_empty_input(self):
        cctx = zstd.ZstdCompressor()

        with self.assertRaisesRegex(ValueError, "no source elements found"):
            cctx.multi_compress_to_buffer([])

        with self.assertRaisesRegex(ValueError, "source elements are empty"):
            cctx.multi_compress_to_buffer([b"", b"", b""])

    def test_list_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        original = [b"foo" * 12, b"bar" * 6]
        frames = [cctx.compress(c) for c in original]
        b = cctx.multi_compress_to_buffer(original)

        self.assertIsInstance(b, zstd.BufferWithSegmentsCollection)

        self.assertEqual(len(b), 2)
        self.assertEqual(b.size(), 44)

        self.assertEqual(b[0].tobytes(), frames[0])
        self.assertEqual(b[1].tobytes(), frames[1])

    def test_buffer_with_segments_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        original = [b"foo" * 4, b"bar" * 6]
        frames = [cctx.compress(c) for c in original]

        offsets = struct.pack(
            "=QQQQ", 0, len(original[0]), len(original[0]), len(original[1])
        )
        segments = zstd.BufferWithSegments(b"".join(original), offsets)

        result = cctx.multi_compress_to_buffer(segments)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.size(), 47)

        self.assertEqual(result[0].tobytes(), frames[0])
        self.assertEqual(result[1].tobytes(), frames[1])

    def test_buffer_with_segments_collection_input(self):
        cctx = zstd.ZstdCompressor(write_checksum=True)

        original = [
            b"foo1",
            b"foo2" * 2,
            b"foo3" * 3,
            b"foo4" * 4,
            b"foo5" * 5,
        ]

        frames = [cctx.compress(c) for c in original]

        b = b"".join([original[0], original[1]])
        b1 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQ", 0, len(original[0]), len(original[0]), len(original[1])
            ),
        )
        b = b"".join([original[2], original[3], original[4]])
        b2 = zstd.BufferWithSegments(
            b,
            struct.pack(
                "=QQQQQQ",
                0,
                len(original[2]),
                len(original[2]),
                len(original[3]),
                len(original[2]) + len(original[3]),
                len(original[4]),
            ),
        )

        c = zstd.BufferWithSegmentsCollection(b1, b2)

        result = cctx.multi_compress_to_buffer(c)

        self.assertEqual(len(result), len(frames))

        for i, frame in enumerate(frames):
            self.assertEqual(result[i].tobytes(), frame)

    def test_multiple_threads(self):
        # threads argument will cause multi-threaded ZSTD APIs to be used, which will
        # make output different.
        refcctx = zstd.ZstdCompressor(write_checksum=True)
        reference = [refcctx.compress(b"x" * 64), refcctx.compress(b"y" * 64)]

        cctx = zstd.ZstdCompressor(write_checksum=True)

        frames = []
        frames.extend(b"x" * 64 for i in range(256))
        frames.extend(b"y" * 64 for i in range(256))

        result = cctx.multi_compress_to_buffer(frames, threads=-1)

        self.assertEqual(len(result), 512)
        for i in range(512):
            if i < 256:
                self.assertEqual(result[i].tobytes(), reference[0])
            else:
                self.assertEqual(result[i].tobytes(), reference[1])
