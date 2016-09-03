import unittest

import zstd

class TestCompressionParameters(unittest.TestCase):
    def test_init_bad_arg_type(self):
        with self.assertRaises(TypeError):
            zstd.CompressionParameters()

        with self.assertRaises(TypeError):
            zstd.CompressionParameters((0, 1))

    def test_get_compression_parameters(self):
        p = zstd.get_compression_parameters(1)
        self.assertIsInstance(p, zstd.CompressionParameters)

        self.assertEqual(p[0], 19)
