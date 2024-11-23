import io
import unittest
from threading import Barrier, Thread

import pytest

import zstandard as zstd


class TestCompressor_threadsafe(unittest.TestCase):
    @pytest.mark.thread_unsafe
    def test_shared_compressor(self):
        num_parallel_threads = 10
        cctx = zstd.ZstdCompressor()
        barrier = Barrier(num_parallel_threads)

        def thread():
            barrier.wait()
            with self.assertRaises(zstd.ZstdError):
                for _ in range(1_000):
                    cctx.compress(io.BytesIO(b"t" * 1048576).getvalue())

        threads = [
            Thread(target=thread)
            for _ in range(num_parallel_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
