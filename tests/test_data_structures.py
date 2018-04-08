import sys
import unittest

import zstandard as zstd

from . common import (
    make_cffi,
)


@make_cffi
class TestCompressionParameters(unittest.TestCase):
    def test_bounds(self):
        zstd.ZstdCompressionParameters(window_log=zstd.WINDOWLOG_MIN,
                                       chain_log=zstd.CHAINLOG_MIN,
                                       hash_log=zstd.HASHLOG_MIN,
                                       search_log=zstd.SEARCHLOG_MIN,
                                       min_match=zstd.SEARCHLENGTH_MIN + 1,
                                       target_length=zstd.TARGETLENGTH_MIN,
                                       compression_strategy=zstd.STRATEGY_FAST)

        zstd.ZstdCompressionParameters(window_log=zstd.WINDOWLOG_MAX,
                                       chain_log=zstd.CHAINLOG_MAX,
                                       hash_log=zstd.HASHLOG_MAX,
                                       search_log=zstd.SEARCHLOG_MAX,
                                       min_match=zstd.SEARCHLENGTH_MAX - 1,
                                       compression_strategy=zstd.STRATEGY_BTULTRA)

    def test_from_level(self):
        p = zstd.ZstdCompressionParameters.from_level(1)
        self.assertIsInstance(p, zstd.CompressionParameters)

        self.assertEqual(p.window_log, 19)

        p = zstd.ZstdCompressionParameters.from_level(-4)
        self.assertEqual(p.window_log, 19)
        self.assertEqual(p.compress_literals, 0)

    def test_members(self):
        p = zstd.ZstdCompressionParameters(window_log=10,
                                           chain_log=6,
                                           hash_log=7,
                                           search_log=4,
                                           min_match=5,
                                           target_length=8,
                                           compression_strategy=1)
        self.assertEqual(p.window_log, 10)
        self.assertEqual(p.chain_log, 6)
        self.assertEqual(p.hash_log, 7)
        self.assertEqual(p.search_log, 4)
        self.assertEqual(p.min_match, 5)
        self.assertEqual(p.target_length, 8)
        self.assertEqual(p.compression_strategy, 1)

        p = zstd.ZstdCompressionParameters(compression_level=2)
        self.assertEqual(p.compression_level, 2)

        p = zstd.ZstdCompressionParameters(threads=4)
        self.assertEqual(p.threads, 4)

        p = zstd.ZstdCompressionParameters(threads=2, job_size=1048576,
                                       overlap_size_log=6)
        self.assertEqual(p.threads, 2)
        self.assertEqual(p.job_size, 1048576)
        self.assertEqual(p.overlap_size_log, 6)

        p = zstd.ZstdCompressionParameters(compression_level=2)
        self.assertEqual(p.compress_literals, 1)

        p = zstd.ZstdCompressionParameters(compress_literals=False)
        self.assertEqual(p.compress_literals, 0)

        p = zstd.ZstdCompressionParameters(compression_level=-1)
        self.assertEqual(p.compression_level, -1)
        self.assertEqual(p.compress_literals, 0)

        p = zstd.ZstdCompressionParameters(compression_level=-2, compress_literals=True)
        self.assertEqual(p.compression_level, -2)
        self.assertEqual(p.compress_literals, 1)

        p = zstd.ZstdCompressionParameters(force_max_window=True)
        self.assertEqual(p.force_max_window, 1)

        p = zstd.ZstdCompressionParameters(enable_ldm=True)
        self.assertEqual(p.enable_ldm, 1)

        p = zstd.ZstdCompressionParameters(ldm_hash_log=7)
        self.assertEqual(p.ldm_hash_log, 7)

        p = zstd.ZstdCompressionParameters(ldm_min_match=6)
        self.assertEqual(p.ldm_min_match, 6)

        p = zstd.ZstdCompressionParameters(ldm_bucket_size_log=7)
        self.assertEqual(p.ldm_bucket_size_log, 7)

        p = zstd.ZstdCompressionParameters(ldm_hash_every_log=8)
        self.assertEqual(p.ldm_hash_every_log, 8)

    def test_estimated_compression_context_size(self):
        p = zstd.ZstdCompressionParameters(window_log=20,
                                           chain_log=16,
                                           hash_log=17,
                                           search_log=1,
                                           min_match=5,
                                           target_length=16,
                                           compression_strategy=zstd.STRATEGY_DFAST)

        # 32-bit has slightly different values from 64-bit.
        self.assertAlmostEqual(p.estimated_compression_context_size(), 1294072,
                               delta=250)


@make_cffi
class TestFrameParameters(unittest.TestCase):
    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            zstd.get_frame_parameters(None)

        # Python 3 doesn't appear to convert unicode to Py_buffer.
        if sys.version_info[0] >= 3:
            with self.assertRaises(TypeError):
                zstd.get_frame_parameters(u'foobarbaz')
        else:
            # CPython will convert unicode to Py_buffer. But CFFI won't.
            if zstd.backend == 'cffi':
                with self.assertRaises(TypeError):
                    zstd.get_frame_parameters(u'foobarbaz')
            else:
                with self.assertRaises(zstd.ZstdError):
                    zstd.get_frame_parameters(u'foobarbaz')

    def test_invalid_input_sizes(self):
        with self.assertRaisesRegexp(zstd.ZstdError, 'not enough data for frame'):
            zstd.get_frame_parameters(b'')

        with self.assertRaisesRegexp(zstd.ZstdError, 'not enough data for frame'):
            zstd.get_frame_parameters(zstd.FRAME_HEADER)

    def test_invalid_frame(self):
        with self.assertRaisesRegexp(zstd.ZstdError, 'Unknown frame descriptor'):
            zstd.get_frame_parameters(b'foobarbaz')

    def test_attributes(self):
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x00\x00')
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Lowest 2 bits indicate a dictionary and length. Here, the dict id is 1 byte.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x01\x00\xff')
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 255)
        self.assertFalse(params.has_checksum)

        # Lowest 3rd bit indicates if checksum is present.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x04\x00')
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertTrue(params.has_checksum)

        # Upper 2 bits indicate content size.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x40\x00\xff\x00')
        self.assertEqual(params.content_size, 511)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Window descriptor is 2nd byte after frame header.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x00\x40')
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Set multiple things.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b'\x45\x40\x0f\x10\x00')
        self.assertEqual(params.content_size, 272)
        self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 15)
        self.assertTrue(params.has_checksum)

    def test_input_types(self):
        v = zstd.FRAME_HEADER + b'\x00\x00'

        mutable_array = bytearray(len(v))
        mutable_array[:] = v

        sources = [
            memoryview(v),
            bytearray(v),
            mutable_array,
        ]

        for source in sources:
            params = zstd.get_frame_parameters(source)
            self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
            self.assertEqual(params.window_size, 1024)
            self.assertEqual(params.dict_id, 0)
            self.assertFalse(params.has_checksum)
