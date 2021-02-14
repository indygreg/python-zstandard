import unittest

import zstandard as zstd


class TestFrameHeaderSize(unittest.TestCase):
    def test_empty(self):
        with self.assertRaisesRegex(
            zstd.ZstdError,
            "could not determine frame header size: Src size " "is incorrect",
        ):
            zstd.frame_header_size(b"")

    def test_too_small(self):
        with self.assertRaisesRegex(
            zstd.ZstdError,
            "could not determine frame header size: Src size " "is incorrect",
        ):
            zstd.frame_header_size(b"foob")

    def test_basic(self):
        # It doesn't matter that it isn't a valid frame.
        self.assertEqual(zstd.frame_header_size(b"long enough but no magic"), 6)


class TestFrameContentSize(unittest.TestCase):
    def test_empty_input(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"")

    def test_too_small(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"foob")

    def test_bad_frame(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "error when determining content size"
        ):
            zstd.frame_content_size(b"invalid frame header")

    def test_unknown(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        frame = cctx.compress(b"foobar")

        self.assertEqual(zstd.frame_content_size(frame), -1)

    def test_empty(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"")

        self.assertEqual(zstd.frame_content_size(frame), 0)

    def test_basic(self):
        cctx = zstd.ZstdCompressor()
        frame = cctx.compress(b"foobar")

        self.assertEqual(zstd.frame_content_size(frame), 6)


class TestDecompressor(unittest.TestCase):
    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()

        self.assertGreater(dctx.memory_size(), 100)
