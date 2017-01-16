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
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        for d in zctx.read_from(bio(chunk), size=len(chunk)):
            pass


def compress_compressor(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        cobj = zctx.compressobj()
        cobj.compress(chunk)
        cobj.flush()


def decompress_one_use(chunks, opts):
    for chunk in chunks:
        zctx = zstd.ZstdDecompressor(**opts)
        zctx.decompress(chunk)


def decompress_reuse(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        zctx.decompress(chunk)


def decompress_write_to(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        with zctx.write_to(bio()) as decompressor:
            decompressor.write(chunk)


def decompress_read_from(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        for d in zctx.read_from(bio(chunk)):
            pass


def decompress_decompressor(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        decompressor = zctx.decompressobj()
        decompressor.decompress(chunk)


def get_chunks(paths, limit_count):
    chunks = []

    def process_file(p):
        with open(p, 'rb') as fh:
            data = fh.read()
            if data:
                chunks.append(data)

    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs.sort()
                for f in sorted(files):
                    try:
                        process_file(os.path.join(root, f))
                        if limit_count and len(chunks) >= limit_count:
                            return chunks
                    except IOError:
                        pass
        else:
            process_file(path)
            if limit_count and len(chunks) >= limit_count:
                return chunks

    return chunks


def format_results(results, title, total_size):
    best = min(results)
    rate = float(total_size) / best[3]

    print(title)
    print('%.6f wall; %.6f CPU; %.6f user; %.6f sys %.2f MB/s (best of %d)' % (
        best[3], best[0], best[1], best[2], rate / 1000000.0, len(results)))


def bench_compression(chunks, opts):
    benches = [
        (compress_one_use, 'compress compress() single use zctx'),
        (compress_reuse, 'compress compress() reuse zctx'),
        (compress_write_to, 'compress write_to()'),
        (compress_write_to_size, 'compress write_to() w/ input size'),
        (compress_read_from, 'compress read_from()'),
        (compress_read_from_size, 'compress read_from() w/ input size'),
        (compress_compressor, 'compress compressobj()'),
    ]

    total_size = sum(map(len, chunks))

    for fn, title in benches:
        results = timer(lambda: fn(chunks, opts))
        format_results(results, title, total_size)


def bench_decompression(chunks, total_size, opts):
    benches = []

    # We can only test simple decompress() if content size was written.
    if opts.get('write_content_size'):
        benches.extend([
            (decompress_one_use, 'decompress() single use zctx'),
            (decompress_reuse, 'decompress() reuse zctx'),
        ])

    benches.extend([
        (decompress_write_to, 'decompress write_to()'),
        (decompress_read_from, 'decompress read_from()'),
        (decompress_decompressor, 'decompress decompressobj()'),
    ])

    dopts = {}
    if opts.get('dict_data'):
        dopts['dict_data'] = opts['dict_data']

    for fn, title in benches:
        results = timer(lambda: fn(chunks, dopts))
        format_results(results, title, total_size)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--no-compression', action='store_true',
                        help='Do not test compression performance')
    parser.add_argument('--no-decompression', action='store_true',
                        help='Do not test decompression performance')
    parser.add_argument('--limit-count', type=int,
                        help='limit number of input files added')
    parser.add_argument('-l', '--level', type=int,
                        help='Compression level')
    parser.add_argument('--write-size', action='store_true',
                        help='Write content size')
    parser.add_argument('--write-checksum', action='store_true',
                        help='Write checksum data')
    parser.add_argument('--dict-size', type=int,
                        help='train a dictionary of this size and test')
    parser.add_argument('--dict-sample-limit', type=int,
                        help='limit how many samples are fed into dictionary '
                             'training')
    parser.add_argument('path', metavar='INPUT', nargs='+')

    args = parser.parse_args()

    opts = {}
    if args.level:
        opts['level'] = args.level
    if args.write_size:
        opts['write_content_size'] = True
    if args.write_checksum:
        opts['write_checksum'] = True

    chunks = get_chunks(args.path, args.limit_count)
    orig_size = sum(map(len, chunks))
    print('%d chunks; %d bytes' % (len(chunks), orig_size))

    if args.dict_size:
        if args.dict_sample_limit:
            training_chunks = chunks[0:args.dict_sample_limit]
        else:
            training_chunks = chunks

        dict_data = zstd.train_dictionary(args.dict_size, training_chunks)
        opts['dict_data'] = dict_data
        print('trained dictionary of size %d (wanted %d)' % (
            len(dict_data), args.dict_size))

    # Obtain compressed chunks to report ratio and other stats.
    zctx = zstd.ZstdCompressor(**opts)
    compressed = []
    ratios = []
    for chunk in chunks:
        c = zctx.compress(chunk)
        compressed.append(c)
        ratios.append(float(len(c)) / float(len(chunk)))

    compressed_size = sum(map(len, compressed))
    ratio = float(compressed_size) / float(orig_size) * 100.0
    bad_count = sum(1 for r in ratios if r >= 1.00)
    good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
    print('compressed size: %d (%.2f%%); smaller: %.2f%%' % (
        compressed_size, ratio, good_ratio))
    print('')

    if not args.no_compression:
        bench_compression(chunks, opts)

    if not args.no_decompression:
        bench_decompression(compressed, orig_size, opts)
