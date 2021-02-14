import unittest

import zstandard as zstd


class TestCompressor_chunker(unittest.TestCase):
    def test_empty(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        chunker = cctx.chunker()

        it = chunker.compress(b"")

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.finish()

        self.assertEqual(next(it), b"\x28\xb5\x2f\xfd\x00\x00\x01\x00\x00")

        with self.assertRaises(StopIteration):
            next(it)

    def test_simple_input(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        it = chunker.compress(b"foobar")

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.compress(b"baz" * 30)

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.finish()

        self.assertEqual(
            next(it),
            b"\x28\xb5\x2f\xfd\x00\x58\x7d\x00\x00\x48\x66\x6f"
            b"\x6f\x62\x61\x72\x62\x61\x7a\x01\x00\xe4\xe4\x8e",
        )

        with self.assertRaises(StopIteration):
            next(it)

    def test_input_size(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker(size=1024)

        it = chunker.compress(b"x" * 1000)

        with self.assertRaises(StopIteration):
            next(it)

        it = chunker.compress(b"y" * 24)

        with self.assertRaises(StopIteration):
            next(it)

        chunks = list(chunker.finish())

        self.assertEqual(
            chunks,
            [
                b"\x28\xb5\x2f\xfd\x60\x00\x03\x65\x00\x00\x18\x78\x78\x79\x02\x00"
                b"\xa0\x16\xe3\x2b\x80\x05"
            ],
        )

        dctx = zstd.ZstdDecompressor()

        self.assertEqual(
            dctx.decompress(b"".join(chunks)), (b"x" * 1000) + (b"y" * 24)
        )

    def test_small_chunk_size(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker(chunk_size=1)

        chunks = list(chunker.compress(b"foo" * 1024))
        self.assertEqual(chunks, [])

        chunks = list(chunker.finish())
        self.assertTrue(all(len(chunk) == 1 for chunk in chunks))

        self.assertEqual(
            b"".join(chunks),
            b"\x28\xb5\x2f\xfd\x00\x58\x55\x00\x00\x18\x66\x6f\x6f\x01\x00"
            b"\xfa\xd3\x77\x43",
        )

        dctx = zstd.ZstdDecompressor()
        self.assertEqual(
            dctx.decompress(b"".join(chunks), max_output_size=10000),
            b"foo" * 1024,
        )

    def test_input_types(self):
        cctx = zstd.ZstdCompressor()

        mutable_array = bytearray(3)
        mutable_array[:] = b"foo"

        sources = [
            memoryview(b"foo"),
            bytearray(b"foo"),
            mutable_array,
        ]

        for source in sources:
            chunker = cctx.chunker()

            self.assertEqual(list(chunker.compress(source)), [])
            self.assertEqual(
                list(chunker.finish()),
                [b"\x28\xb5\x2f\xfd\x00\x58\x19\x00\x00\x66\x6f\x6f"],
            )

    def test_flush(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        self.assertEqual(list(chunker.compress(b"foo" * 1024)), [])
        self.assertEqual(list(chunker.compress(b"bar" * 1024)), [])

        chunks1 = list(chunker.flush())

        self.assertEqual(
            chunks1,
            [
                b"\x28\xb5\x2f\xfd\x00\x58\x8c\x00\x00\x30\x66\x6f\x6f\x62\x61\x72"
                b"\x02\x00\xfa\x03\xfe\xd0\x9f\xbe\x1b\x02"
            ],
        )

        self.assertEqual(list(chunker.flush()), [])
        self.assertEqual(list(chunker.flush()), [])

        self.assertEqual(list(chunker.compress(b"baz" * 1024)), [])

        chunks2 = list(chunker.flush())
        self.assertEqual(len(chunks2), 1)

        chunks3 = list(chunker.finish())
        self.assertEqual(len(chunks2), 1)

        dctx = zstd.ZstdDecompressor()

        self.assertEqual(
            dctx.decompress(
                b"".join(chunks1 + chunks2 + chunks3), max_output_size=10000
            ),
            (b"foo" * 1024) + (b"bar" * 1024) + (b"baz" * 1024),
        )

    def test_compress_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError,
            r"cannot call compress\(\) after compression finished",
        ):
            list(chunker.compress(b"foo"))

    def test_flush_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError, r"cannot call flush\(\) after compression finished"
        ):
            list(chunker.flush())

    def test_finish_after_finish(self):
        cctx = zstd.ZstdCompressor()
        chunker = cctx.chunker()

        list(chunker.compress(b"foo"))
        list(chunker.finish())

        with self.assertRaisesRegex(
            zstd.ZstdError, r"cannot call finish\(\) after compression finished"
        ):
            list(chunker.finish())
