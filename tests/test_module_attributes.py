from __future__ import unicode_literals

import unittest

import zstandard as zstd

from .common import (
    make_cffi,
    TestCase,
)


@make_cffi
class TestModuleAttributes(TestCase):
    def test_version(self):
        self.assertEqual(zstd.ZSTD_VERSION, (1, 4, 4))

        self.assertEqual(zstd.__version__, "0.13.0")

    def test_constants(self):
        self.assertEqual(zstd.MAX_COMPRESSION_LEVEL, 22)
        self.assertEqual(zstd.FRAME_HEADER, b"\x28\xb5\x2f\xfd")

    def test_hasattr(self):
        attrs = (
            "CONTENTSIZE_UNKNOWN",
            "CONTENTSIZE_ERROR",
            "COMPRESSION_RECOMMENDED_INPUT_SIZE",
            "COMPRESSION_RECOMMENDED_OUTPUT_SIZE",
            "DECOMPRESSION_RECOMMENDED_INPUT_SIZE",
            "DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE",
            "MAGIC_NUMBER",
            "FLUSH_BLOCK",
            "FLUSH_FRAME",
            "BLOCKSIZELOG_MAX",
            "BLOCKSIZE_MAX",
            "WINDOWLOG_MIN",
            "WINDOWLOG_MAX",
            "CHAINLOG_MIN",
            "CHAINLOG_MAX",
            "HASHLOG_MIN",
            "HASHLOG_MAX",
            "HASHLOG3_MAX",
            "MINMATCH_MIN",
            "MINMATCH_MAX",
            "SEARCHLOG_MIN",
            "SEARCHLOG_MAX",
            "SEARCHLENGTH_MIN",
            "SEARCHLENGTH_MAX",
            "TARGETLENGTH_MIN",
            "TARGETLENGTH_MAX",
            "LDM_MINMATCH_MIN",
            "LDM_MINMATCH_MAX",
            "LDM_BUCKETSIZELOG_MAX",
            "STRATEGY_FAST",
            "STRATEGY_DFAST",
            "STRATEGY_GREEDY",
            "STRATEGY_LAZY",
            "STRATEGY_LAZY2",
            "STRATEGY_BTLAZY2",
            "STRATEGY_BTOPT",
            "STRATEGY_BTULTRA",
            "STRATEGY_BTULTRA2",
            "DICT_TYPE_AUTO",
            "DICT_TYPE_RAWCONTENT",
            "DICT_TYPE_FULLDICT",
        )

        for a in attrs:
            self.assertTrue(hasattr(zstd, a), a)
