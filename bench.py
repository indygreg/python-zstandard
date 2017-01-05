#!/usr/bin/env python
# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

"""Very hacky script for benchmarking zstd.

Like most benchmarks, results should be treated with skepticism.
"""

import io
import os
import sys
import time


if sys.version_info[0] >= 3:
    bio = io.BytesIO
else:
    import cStringIO
    bio = cStringIO.StringIO


import zstd


def timer(fn, miniter=3, minwall=3.0):
    """Runs fn() multiple times and returns the results.

    Runs for at least ``miniter`` iterations and ``minwall`` wall time.
    """

    results = []
    count = 0

    # Ideally a monotonic clock, but doesn't matter too much.
    wall_begin = time.time()

    while True:
        wstart = time.time()
        start = os.times()
        fn()
        end = os.times()
        wend = time.time()
        count += 1

        user = end[0] - start[0]
        system = end[1] - start[1]
        cpu = user + system
        wall = wend - wstart

        results.append((cpu, user, system, wall))

        # Ensure we run at least ``miniter`` times.
        if count < miniter:
            continue

        # And for ``minwall`` seconds.
        elapsed = wend - wall_begin

        if elapsed < minwall:
            continue

        break

    return results


def compress_one_use(chunks, opts):
    for chunk in chunks:
        zctx = zstd.ZstdCompressor(**opts)
        zctx.compress(chunk)


def compress_reuse(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        zctx.compress(chunk)


def compress_write_to(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        b = bio()
        with zctx.write_to(b) as compressor:
            compressor.write(chunk)


def compress_write_to_size(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        b = bio()
        with zctx.write_to(b, size=len(chunk)) as compressor:
            compressor.write(chunk)


def compress_read_from(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        for d in zctx.read_from(bio(chunk)):
            pass


def compress_read_from_size(chunks, opts):
    zctx = zstd.ZstdCompressor()
    for chunk in chunks:
        for d in zctx.read_from(bio(chunk), size=len(chunk)):
            pass


def compress_compressor(chunks, opts):
    zctx = zstd.ZstdCompressor()
    for chunk in chunks:
        cobj = zctx.compressobj()
        cobj.compress(chunk)
        cobj.flush()


def get_chunks(paths):
    chunks = []

    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    try:
                        with open(os.path.join(root, f), 'rb') as fh:
                            chunks.append(fh.read())
                    except IOError:
                        pass
        else:
            with open(path, 'rb') as fh:
                chunks.append(fh.read())

    return chunks


def format_results(results, title, total_size):
    best = min(results)
    rate = float(total_size) / best[3]

    print(title)
    print('%.6f wall; %.6f CPU; %.6f user; %.6f sys %.2f MB/s (best of %d)' % (
        best[3], best[0], best[1], best[2], rate / 1000000.0, len(results)))


def bench_compression(chunks, opts):
    benches = [
        (compress_one_use, 'compress() single use zctx'),
        (compress_reuse, 'compress() reuse zctx'),
        (compress_write_to, 'write_to()'),
        (compress_write_to_size, 'write_to() w/ input size'),
        (compress_read_from, 'read_from()'),
        (compress_read_from_size, 'read_from() w/ input size'),
        (compress_compressor, 'compressobj()'),
    ]

    total_size = sum(map(len, chunks))
    print('%d chunks; %d bytes' % (len(chunks), total_size))

    for fn, title in benches:
        results = timer(lambda: fn(chunks, opts))
        format_results(results, title, total_size)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--level', type=int,
                        help='Compression level')
    parser.add_argument('--write-size', action='store_true',
                        help='Write content size')
    parser.add_argument('--write-checksum', action='store_true',
                        help='Write checksum data')
    parser.add_argument('path', metavar='INPUT', nargs='+')

    args = parser.parse_args()

    opts = {}
    if args.level:
        opts['level'] = args.level
    if args.write_size:
        opts['write_content_size'] = True
    if args.write_checksum:
        opts['write_checksum'] = True

    chunks = get_chunks(args.path)
    bench_compression(chunks, opts)
