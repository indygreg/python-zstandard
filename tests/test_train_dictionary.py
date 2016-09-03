import sys
import unittest

import zstd


if sys.version_info[0] >= 3:
    int_type = int
else:
    int_type = long


class TestTrainDictionary(unittest.TestCase):
    def test_no_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary()

    def test_bad_args(self):
        with self.assertRaises(TypeError):
            zstd.train_dictionary(8192, u'foo')

        with self.assertRaises(ValueError):
            zstd.train_dictionary(8192, [u'foo'])

    def test_basic(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)
            samples.append(b'baz' * 64)
            samples.append(b'foobaz' * 64)
            samples.append(b'bazfoo' * 64)

        d = zstd.train_dictionary(8192, samples)
        self.assertLessEqual(len(d), 8192)

        dict_id = zstd.dictionary_id(d)
        self.assertIsInstance(dict_id, int_type)
