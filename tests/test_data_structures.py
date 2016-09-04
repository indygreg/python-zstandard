try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import hypothesis
    import hypothesis.strategies as strategies
except ImportError:
    hypothesis = None

import zstd

class TestCompressionParameters(unittest.TestCase):
    def test_init_bad_arg_type(self):
        with self.assertRaises(TypeError):
            zstd.CompressionParameters()

        with self.assertRaises(TypeError):
            zstd.CompressionParameters(0, 1)

    def test_bounds(self):
        zstd.CompressionParameters(zstd.WINDOWLOG_MIN,
                                   zstd.CHAINLOG_MIN,
                                   zstd.HASHLOG_MIN,
                                   zstd.SEARCHLOG_MIN,
                                   zstd.SEARCHLENGTH_MIN,
                                   zstd.TARGETLENGTH_MIN,
                                   zstd.STRATEGY_FAST)

        zstd.CompressionParameters(zstd.WINDOWLOG_MAX,
                                   zstd.CHAINLOG_MAX,
                                   zstd.HASHLOG_MAX,
                                   zstd.SEARCHLOG_MAX,
                                   zstd.SEARCHLENGTH_MAX,
                                   zstd.TARGETLENGTH_MAX,
                                   zstd.STRATEGY_BTOPT)

    def test_get_compression_parameters(self):
        p = zstd.get_compression_parameters(1)
        self.assertIsInstance(p, zstd.CompressionParameters)

        self.assertEqual(p[0], 19)

if hypothesis:
    s_windowlog = strategies.integers(min_value=zstd.WINDOWLOG_MIN,
                                      max_value=zstd.WINDOWLOG_MAX)
    s_chainlog = strategies.integers(min_value=zstd.CHAINLOG_MIN,
                                     max_value=zstd.CHAINLOG_MAX)
    s_hashlog = strategies.integers(min_value=zstd.HASHLOG_MIN,
                                    max_value=zstd.HASHLOG_MAX)
    s_searchlog = strategies.integers(min_value=zstd.SEARCHLOG_MIN,
                                      max_value=zstd.SEARCHLOG_MAX)
    s_searchlength = strategies.integers(min_value=zstd.SEARCHLENGTH_MIN,
                                         max_value=zstd.SEARCHLENGTH_MAX)
    s_targetlength = strategies.integers(min_value=zstd.TARGETLENGTH_MIN,
                                         max_value=zstd.TARGETLENGTH_MAX)
    s_strategy = strategies.sampled_from((zstd.STRATEGY_FAST,
                                          zstd.STRATEGY_DFAST,
                                          zstd.STRATEGY_GREEDY,
                                          zstd.STRATEGY_LAZY,
                                          zstd.STRATEGY_LAZY2,
                                          zstd.STRATEGY_BTLAZY2,
                                          zstd.STRATEGY_BTOPT))

    class TestCompressionParametersHypothesis(unittest.TestCase):
        @hypothesis.given(s_windowlog, s_chainlog, s_hashlog, s_searchlog,
                          s_searchlength, s_targetlength, s_strategy)
        def test_valid_init(self, windowlog, chainlog, hashlog, searchlog,
                            searchlength, targetlength, strategy):
            p = zstd.CompressionParameters(windowlog, chainlog, hashlog,
                                           searchlog, searchlength,
                                           targetlength, strategy)
            self.assertEqual(tuple(p),
                             (windowlog, chainlog, hashlog, searchlog,
                              searchlength, targetlength, strategy))
