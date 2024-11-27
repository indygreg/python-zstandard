import unittest
from threading import Barrier, Lock, Thread

import pytest

import zstandard as zstd


class TestCompressor_threadsafe(unittest.TestCase):
    @pytest.mark.thread_unsafe
    def test_shared_compressor(self):
        num_parallel_threads = 10
        cctx = zstd.ZstdCompressor()
        barrier = Barrier(num_parallel_threads)
        raised_exceptions = 0
        raised_exceptions_lock = Lock()

        def thread():
            nonlocal raised_exceptions

            barrier.wait()
            try:
                for _ in range(1_000):
                    cctx.compress(b"t" * 1048576)
            except zstd.ZstdError:
                with raised_exceptions_lock:
                    raised_exceptions += 1

        threads = [
            Thread(target=thread)
            for _ in range(num_parallel_threads)
        ]
        # time.sleep(10)
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert raised_exceptions == num_parallel_threads - 1
