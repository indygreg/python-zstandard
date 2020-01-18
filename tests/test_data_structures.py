import sys
import unittest

import zstandard as zstd

from .common import (
    make_cffi,
    TestCase,
)


@make_cffi
class TestCompressionParameters(TestCase):
    def test_bounds(self):
        zstd.ZstdCompressionParameters(
            window_log=zstd.WINDOWLOG_MIN,
            chain_log=zstd.CHAINLOG_MIN,
            hash_log=zstd.HASHLOG_MIN,
            search_log=zstd.SEARCHLOG_MIN,
            min_match=zstd.MINMATCH_MIN + 1,
            target_length=zstd.TARGETLENGTH_MIN,
            strategy=zstd.STRATEGY_FAST,
        )

        zstd.ZstdCompressionParameters(
            window_log=zstd.WINDOWLOG_MAX,
            chain_log=zstd.CHAINLOG_MAX,
            hash_log=zstd.HASHLOG_MAX,
            search_log=zstd.SEARCHLOG_MAX,
            min_match=zstd.MINMATCH_MAX - 1,
            target_length=zstd.TARGETLENGTH_MAX,
            strategy=zstd.STRATEGY_BTULTRA2,
        )

    def test_from_level(self):
        p = zstd.ZstdCompressionParameters.from_level(1)
        self.assertIsInstance(p, zstd.CompressionParameters)

        self.assertEqual(p.window_log, 19)

        p = zstd.ZstdCompressionParameters.from_level(-4)
        self.assertEqual(p.window_log, 19)

    def test_members(self):
        p = zstd.ZstdCompressionParameters(
            window_log=10,
            chain_log=6,
            hash_log=7,
            search_log=4,
            min_match=5,
            target_length=8,
            strategy=1,
        )
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

        p = zstd.ZstdCompressionParameters(
            threads=2, job_size=1048576, overlap_log=6
        )
        self.assertEqual(p.threads, 2)
        self.assertEqual(p.job_size, 1048576)
        self.assertEqual(p.overlap_log, 6)
        self.assertEqual(p.overlap_size_log, 6)

        p = zstd.ZstdCompressionParameters(compression_level=-1)
        self.assertEqual(p.compression_level, -1)

        p = zstd.ZstdCompressionParameters(compression_level=-2)
        self.assertEqual(p.compression_level, -2)

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

        p = zstd.ZstdCompressionParameters(ldm_hash_rate_log=8)
        self.assertEqual(p.ldm_hash_every_log, 8)
        self.assertEqual(p.ldm_hash_rate_log, 8)

    def test_estimated_compression_context_size(self):
        p = zstd.ZstdCompressionParameters(
            window_log=20,
            chain_log=16,
            hash_log=17,
            search_log=1,
            min_match=5,
            target_length=16,
            strategy=zstd.STRATEGY_DFAST,
        )

        # 32-bit has slightly different values from 64-bit.
        self.assertAlmostEqual(
            p.estimated_compression_context_size(), 1294464, delta=400
        )

    def test_strategy(self):
        with self.assertRaisesRegex(
            ValueError, "cannot specify both compression_strategy"
        ):
            zstd.ZstdCompressionParameters(strategy=0, compression_strategy=0)

        p = zstd.ZstdCompressionParameters(strategy=2)
        self.assertEqual(p.compression_strategy, 2)

        p = zstd.ZstdCompressionParameters(strategy=3)
        self.assertEqual(p.compression_strategy, 3)

    def test_ldm_hash_rate_log(self):
        with self.assertRaisesRegex(
            ValueError, "cannot specify both ldm_hash_rate_log"
        ):
            zstd.ZstdCompressionParameters(
                ldm_hash_rate_log=8, ldm_hash_every_log=4
            )

        p = zstd.ZstdCompressionParameters(ldm_hash_rate_log=8)
        self.assertEqual(p.ldm_hash_every_log, 8)

        p = zstd.ZstdCompressionParameters(ldm_hash_every_log=16)
        self.assertEqual(p.ldm_hash_every_log, 16)

    def test_overlap_log(self):
        with self.assertRaisesRegex(
            ValueError, "cannot specify both overlap_log"
        ):
            zstd.ZstdCompressionParameters(overlap_log=1, overlap_size_log=9)

        p = zstd.ZstdCompressionParameters(overlap_log=2)
        self.assertEqual(p.overlap_log, 2)
        self.assertEqual(p.overlap_size_log, 2)

        p = zstd.ZstdCompressionParameters(overlap_size_log=4)
        self.assertEqual(p.overlap_log, 4)
        self.assertEqual(p.overlap_size_log, 4)


@make_cffi
class TestFrameParameters(TestCase):
    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            zstd.get_frame_parameters(None)

        # Python 3 doesn't appear to convert unicode to Py_buffer.
        if sys.version_info[0] >= 3:
            with self.assertRaises(TypeError):
                zstd.get_frame_parameters(u"foobarbaz")
        else:
            # CPython will convert unicode to Py_buffer. But CFFI won't.
            if zstd.backend == "cffi":
                with self.assertRaises(TypeError):
                    zstd.get_frame_parameters(u"foobarbaz")
            else:
                with self.assertRaises(zstd.ZstdError):
                    zstd.get_frame_parameters(u"foobarbaz")

    def test_invalid_input_sizes(self):
        with self.assertRaisesRegex(
            zstd.ZstdError, "not enough data for frame"
        ):
            zstd.get_frame_parameters(b"")

        with self.assertRaisesRegex(
            zstd.ZstdError, "not enough data for frame"
        ):
            zstd.get_frame_parameters(zstd.FRAME_HEADER)

    def test_invalid_frame(self):
        with self.assertRaisesRegex(zstd.ZstdError, "Unknown frame descriptor"):
            zstd.get_frame_parameters(b"foobarbaz")

    def test_attributes(self):
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b"\x00\x00")
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Lowest 2 bits indicate a dictionary and length. Here, the dict id is 1 byte.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b"\x01\x00\xff")
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 255)
        self.assertFalse(params.has_checksum)

        # Lowest 3rd bit indicates if checksum is present.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b"\x04\x00")
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertTrue(params.has_checksum)

        # Upper 2 bits indicate content size.
        params = zstd.get_frame_parameters(
            zstd.FRAME_HEADER + b"\x40\x00\xff\x00"
        )
        self.assertEqual(params.content_size, 511)
        self.assertEqual(params.window_size, 1024)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Window descriptor is 2nd byte after frame header.
        params = zstd.get_frame_parameters(zstd.FRAME_HEADER + b"\x00\x40")
        self.assertEqual(params.content_size, zstd.CONTENTSIZE_UNKNOWN)
        self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 0)
        self.assertFalse(params.has_checksum)

        # Set multiple things.
        params = zstd.get_frame_parameters(
            zstd.FRAME_HEADER + b"\x45\x40\x0f\x10\x00"
        )
        self.assertEqual(params.content_size, 272)
        self.assertEqual(params.window_size, 262144)
        self.assertEqual(params.dict_id, 15)
        self.assertTrue(params.has_checksum)

    def test_input_types(self):
        v = zstd.FRAME_HEADER + b"\x00\x00"

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
