import io
import os
import sys
import unittest

try:
    import hypothesis
    import hypothesis.strategies as strategies
except ImportError:
    raise unittest.SkipTest("hypothesis not available")

import zstandard as zstd

from .common import (
    make_cffi,
    TestCase,
)


s_windowlog = strategies.integers(
    min_value=zstd.WINDOWLOG_MIN, max_value=zstd.WINDOWLOG_MAX
)
s_chainlog = strategies.integers(
    min_value=zstd.CHAINLOG_MIN, max_value=zstd.CHAINLOG_MAX
)
s_hashlog = strategies.integers(
    min_value=zstd.HASHLOG_MIN, max_value=zstd.HASHLOG_MAX
)
s_searchlog = strategies.integers(
    min_value=zstd.SEARCHLOG_MIN, max_value=zstd.SEARCHLOG_MAX
)
s_minmatch = strategies.integers(
    min_value=zstd.MINMATCH_MIN, max_value=zstd.MINMATCH_MAX
)
s_targetlength = strategies.integers(
    min_value=zstd.TARGETLENGTH_MIN, max_value=zstd.TARGETLENGTH_MAX
)
s_strategy = strategies.sampled_from(
    (
        zstd.STRATEGY_FAST,
        zstd.STRATEGY_DFAST,
        zstd.STRATEGY_GREEDY,
        zstd.STRATEGY_LAZY,
        zstd.STRATEGY_LAZY2,
        zstd.STRATEGY_BTLAZY2,
        zstd.STRATEGY_BTOPT,
        zstd.STRATEGY_BTULTRA,
        zstd.STRATEGY_BTULTRA2,
    )
)


@make_cffi
@unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
class TestCompressionParametersHypothesis(TestCase):
    @hypothesis.given(
        s_windowlog,
        s_chainlog,
        s_hashlog,
        s_searchlog,
        s_minmatch,
        s_targetlength,
        s_strategy,
    )
    def test_valid_init(
        self,
        windowlog,
        chainlog,
        hashlog,
        searchlog,
        minmatch,
        targetlength,
        strategy,
    ):
        zstd.ZstdCompressionParameters(
            window_log=windowlog,
            chain_log=chainlog,
            hash_log=hashlog,
            search_log=searchlog,
            min_match=minmatch,
            target_length=targetlength,
            strategy=strategy,
        )

    @hypothesis.given(
        s_windowlog,
        s_chainlog,
        s_hashlog,
        s_searchlog,
        s_minmatch,
        s_targetlength,
        s_strategy,
    )
    def test_estimated_compression_context_size(
        self,
        windowlog,
        chainlog,
        hashlog,
        searchlog,
        minmatch,
        targetlength,
        strategy,
    ):
        if minmatch == zstd.MINMATCH_MIN and strategy in (
            zstd.STRATEGY_FAST,
            zstd.STRATEGY_GREEDY,
        ):
            minmatch += 1
        elif minmatch == zstd.MINMATCH_MAX and strategy != zstd.STRATEGY_FAST:
            minmatch -= 1

        p = zstd.ZstdCompressionParameters(
            window_log=windowlog,
            chain_log=chainlog,
            hash_log=hashlog,
            search_log=searchlog,
            min_match=minmatch,
            target_length=targetlength,
            strategy=strategy,
        )
        size = p.estimated_compression_context_size()
