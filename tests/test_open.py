import io
import os
import tempfile
import unittest

import zstandard as zstd


class TestOpen(unittest.TestCase):
    def test_write_binary_fileobj(self):
        buffer = io.BytesIO()

        fh = zstd.open(buffer, "wb")
        fh.write(b"foo" * 1024)
        self.assertFalse(fh.closed)
        self.assertFalse(buffer.closed)

        fh.close()
        self.assertTrue(fh.closed)
        self.assertFalse(buffer.closed)

    def test_write_binary_filename(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "testfile")

            fh = zstd.open(p, "wb")
            fh.write(b"foo" * 1024)
            self.assertFalse(fh.closed)

            fh.close()
            self.assertTrue(fh.closed)

    def test_write_text_fileobj(self):
        buffer = io.BytesIO()

        fh = zstd.open(buffer, "w")
        fh.write("foo")
        fh.write("foo")

    def test_write_text_filename(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "testfile")

            fh = zstd.open(p, "w")
            self.assertIsInstance(fh, io.TextIOWrapper)

            fh.write("foo\n")
            fh.write("bar\n")
            fh.close()
            self.assertTrue(fh.closed)

            with zstd.open(p, "r") as fh:
                self.assertEqual(fh.read(), "foo\nbar\n")

    def test_read_binary_fileobj(self):
        cctx = zstd.ZstdCompressor()
        buffer = io.BytesIO(cctx.compress(b"foo" * 1024))

        fh = zstd.open(buffer, "rb")

        self.assertEqual(fh.read(6), b"foofoo")
        self.assertFalse(fh.closed)
        self.assertFalse(buffer.closed)

        fh.close()
        self.assertTrue(fh.closed)
        self.assertFalse(buffer.closed)

        buffer = io.BytesIO(cctx.compress(b"foo" * 1024))

        with zstd.open(buffer, "rb", closefd=True) as fh:
            self.assertEqual(fh.read(), b"foo" * 1024)

        self.assertTrue(fh.closed)
        self.assertTrue(buffer.closed)

    def test_read_binary_filename(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "testfile")
            with open(p, "wb") as fh:
                cctx = zstd.ZstdCompressor()
                fh.write(cctx.compress(b"foo" * 1024))

            fh = zstd.open(p, "rb")

            self.assertEqual(fh.read(6), b"foofoo")
            self.assertEqual(len(fh.read()), 1024 * 3 - 6)
            self.assertFalse(fh.closed)

            fh.close()
            self.assertTrue(fh.closed)

    def test_read_text_fileobj(self):
        cctx = zstd.ZstdCompressor()
        buffer = io.BytesIO(cctx.compress(b"foo\n" * 1024))

        fh = zstd.open(buffer, "r")
        self.assertIsInstance(fh, io.TextIOWrapper)

        self.assertEqual(fh.readline(), "foo\n")

        fh.close()
        self.assertTrue(fh.closed)
        self.assertFalse(buffer.closed)

    def test_read_text_filename(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "testfile")
            cctx = zstd.ZstdCompressor()
            with open(p, "wb") as fh:
                fh.write(cctx.compress(b"foo\n" * 1024))

            fh = zstd.open(p, "r")

            self.assertEqual(fh.read(4), "foo\n")
            self.assertEqual(fh.readline(), "foo\n")
            self.assertFalse(fh.closed)

            fh.close()
            self.assertTrue(fh.closed)
