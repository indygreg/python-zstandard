import unittest

import zstandard as zstd


class TestDecompressor_content_dict_chain(unittest.TestCase):
    def test_bad_inputs_simple(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaises(TypeError):
            dctx.decompress_content_dict_chain(b"foo")

        with self.assertRaises(TypeError):
            dctx.decompress_content_dict_chain((b"foo", b"bar"))

        with self.assertRaisesRegex(ValueError, "empty input chain"):
            dctx.decompress_content_dict_chain([])

        with self.assertRaisesRegex(ValueError, "chunk 0 must be bytes"):
            dctx.decompress_content_dict_chain([u"foo"])

        with self.assertRaisesRegex(ValueError, "chunk 0 must be bytes"):
            dctx.decompress_content_dict_chain([True])

        with self.assertRaisesRegex(
            ValueError, "chunk 0 is too small to contain a zstd frame"
        ):
            dctx.decompress_content_dict_chain([zstd.FRAME_HEADER])

        with self.assertRaisesRegex(
            ValueError, "chunk 0 is not a valid zstd frame"
        ):
            dctx.decompress_content_dict_chain([b"foo" * 8])

        no_size = zstd.ZstdCompressor(write_content_size=False).compress(
            b"foo" * 64
        )

        with self.assertRaisesRegex(
            ValueError, "chunk 0 missing content size in frame"
        ):
            dctx.decompress_content_dict_chain([no_size])

        # Corrupt first frame.
        frame = zstd.ZstdCompressor().compress(b"foo" * 64)
        frame = frame[0:12] + frame[15:]
        with self.assertRaisesRegex(
            zstd.ZstdError, "chunk 0 did not decompress full frame"
        ):
            dctx.decompress_content_dict_chain([frame])

    def test_bad_subsequent_input(self):
        initial = zstd.ZstdCompressor().compress(b"foo" * 64)

        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegex(ValueError, "chunk 1 must be bytes"):
            dctx.decompress_content_dict_chain([initial, u"foo"])

        with self.assertRaisesRegex(ValueError, "chunk 1 must be bytes"):
            dctx.decompress_content_dict_chain([initial, None])

        with self.assertRaisesRegex(
            ValueError, "chunk 1 is too small to contain a zstd frame"
        ):
            dctx.decompress_content_dict_chain([initial, zstd.FRAME_HEADER])

        with self.assertRaisesRegex(
            ValueError, "chunk 1 is not a valid zstd frame"
        ):
            dctx.decompress_content_dict_chain([initial, b"foo" * 8])

        no_size = zstd.ZstdCompressor(write_content_size=False).compress(
            b"foo" * 64
        )

        with self.assertRaisesRegex(
            ValueError, "chunk 1 missing content size in frame"
        ):
            dctx.decompress_content_dict_chain([initial, no_size])

        # Corrupt second frame.
        cctx = zstd.ZstdCompressor(
            dict_data=zstd.ZstdCompressionDict(b"foo" * 64)
        )
        frame = cctx.compress(b"bar" * 64)
        frame = frame[0:12] + frame[15:]

        with self.assertRaisesRegex(
            zstd.ZstdError, "chunk 1 did not decompress full frame"
        ):
            dctx.decompress_content_dict_chain([initial, frame])

    def test_simple(self):
        original = [
            b"foo" * 64,
            b"foobar" * 64,
            b"baz" * 64,
            b"foobaz" * 64,
            b"foobarbaz" * 64,
        ]

        chunks = []
        chunks.append(zstd.ZstdCompressor().compress(original[0]))
        for i, chunk in enumerate(original[1:]):
            d = zstd.ZstdCompressionDict(original[i])
            cctx = zstd.ZstdCompressor(dict_data=d)
            chunks.append(cctx.compress(chunk))

        for i in range(1, len(original)):
            chain = chunks[0:i]
            expected = original[i - 1]
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress_content_dict_chain(chain)
            self.assertEqual(decompressed, expected)
