import struct
import sys
import unittest

import zstandard as zstd

from .common import (
    generate_samples,
    make_cffi,
    random_input_data,
    TestCase,
)

if sys.version_info[0] >= 3:
    int_type = int
else:
    int_type = long


@make_cffi
class TestTrainDictionary(TestCase):
    def test_no_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary()

    def test_bad_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary(8192, u"foo")

        with self.assertRaises(ValueError):
            zstd.train_dictionary(8192, [u"foo"])

    def test_no_params(self):
        d = zstd.train_dictionary(8192, random_input_data())
        self.assertIsInstance(d.dict_id(), int_type)

        # The dictionary ID may be different across platforms.
        expected = b"\x37\xa4\x30\xec" + struct.pack("<I", d.dict_id())

        data = d.as_bytes()
        self.assertEqual(data[0:8], expected)

    def test_basic(self):
        d = zstd.train_dictionary(8192, generate_samples(), k=64, d=16)
        self.assertIsInstance(d.dict_id(), int_type)

        data = d.as_bytes()
        self.assertEqual(data[0:4], b"\x37\xa4\x30\xec")

        self.assertEqual(d.k, 64)
        self.assertEqual(d.d, 16)

    def test_set_dict_id(self):
        d = zstd.train_dictionary(
            8192, generate_samples(), k=64, d=16, dict_id=42
        )
        self.assertEqual(d.dict_id(), 42)

    def test_optimize(self):
        d = zstd.train_dictionary(
            8192, generate_samples(), threads=-1, steps=1, d=16
        )

        # This varies by platform.
        self.assertIn(d.k, (50, 2000))
        self.assertEqual(d.d, 16)


@make_cffi
class TestCompressionDict(TestCase):
    def test_bad_mode(self):
        with self.assertRaisesRegex(ValueError, "invalid dictionary load mode"):
            zstd.ZstdCompressionDict(b"foo", dict_type=42)

    def test_bad_precompute_compress(self):
        d = zstd.train_dictionary(8192, generate_samples(), k=64, d=16)

        with self.assertRaisesRegex(
            ValueError, "must specify one of level or "
        ):
            d.precompute_compress()

        with self.assertRaisesRegex(
            ValueError, "must only specify one of level or "
        ):
            d.precompute_compress(
                level=3, compression_params=zstd.CompressionParameters()
            )

    def test_precompute_compress_rawcontent(self):
        d = zstd.ZstdCompressionDict(
            b"dictcontent" * 64, dict_type=zstd.DICT_TYPE_RAWCONTENT
        )
        d.precompute_compress(level=1)

        d = zstd.ZstdCompressionDict(
            b"dictcontent" * 64, dict_type=zstd.DICT_TYPE_FULLDICT
        )
        with self.assertRaisesRegex(
            zstd.ZstdError, "unable to precompute dictionary"
        ):
            d.precompute_compress(level=1)
