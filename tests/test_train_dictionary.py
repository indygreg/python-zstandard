import sys
import unittest

import zstandard as zstd

from . common import (
    make_cffi,
)

if sys.version_info[0] >= 3:
    int_type = int
else:
    int_type = long


def generate_samples():
    inputs = [
        b'foo',
        b'bar',
        b'abcdef',
        b'sometext',
        b'baz',
    ]

    samples = []

    for i in range(128):
        samples.append(inputs[i % 5])
        samples.append(inputs[i % 5] * (i + 3))
        samples.append(inputs[-(i % 5)] * (i + 2))

    return samples


@make_cffi
class TestTrainDictionary(unittest.TestCase):
    def test_no_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary()

    def test_bad_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary(8192, u'foo')

        with self.assertRaises(ValueError):
            zstd.train_dictionary(8192, [u'foo'])

    def test_no_params(self):
        d = zstd.train_dictionary(8192, generate_samples())
        self.assertIsInstance(d.dict_id(), int_type)

        data = d.as_bytes()
        self.assertEqual(data[0:8], b'\x37\xa4\x30\xec\x6e\x9a\x80\x25')

    def test_basic(self):
        d = zstd.train_dictionary(8192, generate_samples(), k=64, d=16)
        self.assertIsInstance(d.dict_id(), int_type)

        data = d.as_bytes()
        self.assertEqual(data[0:4], b'\x37\xa4\x30\xec')

        self.assertEqual(d.k, 64)
        self.assertEqual(d.d, 16)

    def test_set_dict_id(self):
        d = zstd.train_dictionary(8192, generate_samples(), k=64, d=16,
                                  dict_id=42)
        self.assertEqual(d.dict_id(), 42)

    def test_optimize(self):
        d = zstd.train_dictionary(8192, generate_samples(), threads=-1, steps=1,
                                  d=16)

        self.assertEqual(d.k, 50)
        self.assertEqual(d.d, 16)
