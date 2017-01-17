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


def compress_compressobj(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        cobj = zctx.compressobj()
        cobj.compress(chunk)
        cobj.flush()


def compress_compressobj_size(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    for chunk in chunks:
        cobj = zctx.compressobj(size=len(chunk))
        cobj.compress(chunk)
        cobj.flush()


def compress_stream_write_to(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    b = bio()
    with zctx.write_to(b) as compressor:
        for chunk in chunks:
            compressor.write(chunk)
            compressor.flush()


def compress_stream_compressobj(chunks, opts):
    zctx = zstd.ZstdCompressor(**opts)
    compressor = zctx.compressobj()
    flush = zstd.COMPRESSOBJ_FLUSH_BLOCK
    for chunk in chunks:
        compressor.compress(chunk)
        compressor.flush(flush)


def compress_content_dict_compress(chunks, opts):
    zstd.ZstdCompressor(**opts).compress(chunks[0])
    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zstd.ZstdCompressor(dict_data=d, **opts).compress(chunk)


def compress_content_dict_write_to(chunks, opts, use_size=False):
    zctx = zstd.ZstdCompressor(**opts)
    b = bio()
    with zctx.write_to(b, size=len(chunks[0]) if use_size else 0) as compressor:
        compressor.write(chunks[0])

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        b = bio()
        zctx = zstd.ZstdCompressor(dict_data=d, **opts)
        with zctx.write_to(b, size=len(chunk) if use_size else 0) as compressor:
            compressor.write(chunk)


def compress_content_dict_write_to_size(chunks, opts):
    compress_content_dict_write_to(chunks, opts, use_size=True)


def compress_content_dict_read_from(chunks, opts, use_size=False):
    zctx = zstd.ZstdCompressor(**opts)
    size = len(chunks[0]) if use_size else 0
    for o in zctx.read_from(bio(chunks[0]), size=size):
        pass

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zctx = zstd.ZstdCompressor(dict_data=d, **opts)
        size = len(chunk) if use_size else 0
        for o in zctx.read_from(bio(chunk), size=size):
            pass


def compress_content_dict_read_from_size(chunks, opts):
    compress_content_dict_read_from(chunks, opts, use_size=True)


def compress_content_dict_compressobj(chunks, opts, use_size=False):
    zctx = zstd.ZstdCompressor(**opts)
    cobj = zctx.compressobj(size=len(chunks[0]) if use_size else 0)
    cobj.compress(chunks[0])
    cobj.flush()

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zctx = zstd.ZstdCompressor(dict_data=d, **opts)
        cobj = zctx.compressobj(len(chunk) if use_size else 0)
        cobj.compress(chunk)
        cobj.flush()


def compress_content_dict_compressobj_size(chunks, opts):
    compress_content_dict_compressobj(chunks, opts, use_size=True)


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


def decompress_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        decompressor = zctx.decompressobj()
        decompressor.decompress(chunk)


def decompress_stream_write_to(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    with zctx.write_to(bio()) as decompressor:
        for chunk in chunks:
            decompressor.write(chunk)


def decompress_stream_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    decompressor = zctx.decompressobj()
    for chunk in chunks:
        decompressor.decompress(chunk)


def decompress_content_dict_decompress(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = zctx.decompress(chunks[0])

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = zctx.decompress(chunk)


def decompress_content_dict_write_to(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    b = bio()
    with zctx.write_to(b) as decompressor:
        decompressor.write(chunks[0])

    last = b.getvalue()
    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        b = bio()
        with zctx.write_to(b) as decompressor:
            decompressor.write(chunk)
            last = b.getvalue()


def decompress_content_dict_read_from(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = b''.join(zctx.read_from(bio(chunks[0])))

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = b''.join(zctx.read_from(bio(chunk)))


def decompress_content_dict_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = zctx.decompressobj().decompress(chunks[0])

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = zctx.decompressobj().decompress(chunk)


def decompress_content_dict_chain_api(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.decompress_content_dict_chain(chunks)


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


def format_results(results, title, prefix, total_size):
    best = min(results)
    rate = float(total_size) / best[3]

    print('%s %s' % (prefix, title))
    print('%.6f wall; %.6f CPU; %.6f user; %.6f sys %.2f MB/s (best of %d)' % (
        best[3], best[0], best[1], best[2], rate / 1000000.0, len(results)))


def bench_discrete_compression(chunks, opts):
    benches = [
        (compress_one_use, 'compress() single use zctx'),
        (compress_reuse, 'compress() reuse zctx'),
        (compress_write_to, 'write_to()'),
        (compress_write_to_size, 'write_to() w/ input size'),
        (compress_read_from, 'read_from()'),
        (compress_read_from_size, 'read_from() w/ input size'),
        (compress_compressobj, 'compressobj()'),
        (compress_compressobj_size, 'compressobj() w/ input size'),
    ]

    total_size = sum(map(len, chunks))

    if 'dict_data' in opts:
        prefix = 'compress discrete dict'
    else:
        prefix = 'compress discrete'

    for fn, title in benches:
        results = timer(lambda: fn(chunks, opts))
        format_results(results, title, prefix, total_size)


def bench_discrete_decompression(chunks, total_size, opts):
    benches = []

    # We can only test simple decompress() if content size was written.
    if opts.get('write_content_size'):
        benches.extend([
            (decompress_one_use, 'decompress() single use zctx'),
            (decompress_reuse, 'decompress() reuse zctx'),
        ])

    benches.extend([
        (decompress_write_to, 'write_to()'),
        (decompress_read_from, 'read_from()'),
        (decompress_decompressobj, 'decompressobj()'),
    ])

    dopts = {}
    if opts.get('dict_data'):
        dopts['dict_data'] = opts['dict_data']
        prefix = 'decompress discrete dict'
    else:
        prefix = 'decompress discrete'

    for fn, title in benches:
        results = timer(lambda: fn(chunks, dopts))
        format_results(results, title, prefix, total_size)


def bench_stream_compression(chunks, opts):
    benches = [
        (compress_stream_write_to, 'write_to()'),
        (compress_stream_compressobj, 'compressobj()'),
    ]

    total_size = sum(map(len, chunks))

    for fn, title in benches:
        results = timer(lambda: fn(chunks, opts))
        format_results(results, title, 'compress stream', total_size)


def bench_stream_decompression(chunks, total_size, opts):
    benches = [
        (decompress_stream_write_to, 'write_to()'),
        (decompress_stream_decompressobj, 'decompressobj()'),
    ]

    for fn, title in benches:
        results = timer(lambda: fn(chunks, {}))
        format_results(results, title, 'decompress stream', total_size)


def bench_content_dict_compression(chunks, opts):
    benches = [
        (compress_content_dict_compress, 'compress()'),
        (compress_content_dict_write_to, 'write_to()'),
        (compress_content_dict_write_to_size, 'write_to() w/ input size'),
        (compress_content_dict_read_from, 'read_from()'),
        (compress_content_dict_read_from_size, 'read_from() w/ input size'),
        (compress_content_dict_compressobj, 'compressobj()'),
        (compress_content_dict_compressobj_size, 'compressobj() w/ input size'),
    ]

    total_size = sum(map(len, chunks))

    for fn, title in benches:
        results = timer(lambda: fn(chunks, opts))
        format_results(results, title, 'compress content dict', total_size)


def bench_content_dict_decompression(chunks, total_size, opts):
    benches = []

    if opts.get('write_content_size'):
        benches.append((decompress_content_dict_decompress, 'decompress()'))

    benches.extend([
        (decompress_content_dict_write_to, 'write_to()'),
        (decompress_content_dict_read_from, 'read_from()'),
        (decompress_content_dict_decompressobj, 'decompressobj()'),
        (decompress_content_dict_chain_api, 'decompress_content_dict_chain()'),
    ])

    for fn, title in benches:
        results = timer(lambda: fn(chunks, {}))
        format_results(results, title, 'decompress content dict', total_size)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    group = parser.add_argument_group('Compression Modes')
    group.add_argument('--discrete', action='store_true',
                       help='Compress each input independently')
    group.add_argument('--stream', action='store_true',
                       help='Feed each input into a stream and emit '
                            'flushed blocks')
    group.add_argument('--content-dict', action='store_true',
                       help='Compress each input using the previous as a '
                            'content dictionary')
    group.add_argument('--discrete-dict', action='store_true',
                       help='Compress each input independently with a '
                            'dictionary')

    parser.add_argument('--no-compression', action='store_true',
                        help='Do not test compression performance')
    parser.add_argument('--no-decompression', action='store_true',
                        help='Do not test decompression performance')
    parser.add_argument('--limit-count', type=int,
                        help='limit number of input files added')
    parser.add_argument('-l', '--level', type=int,
                        help='Compression level')
    parser.add_argument('--write-size', action='store_true',
                        help='Write content size to zstd frames')
    parser.add_argument('--write-checksum', action='store_true',
                        help='Write checksum data to zstd frames')
    parser.add_argument('--dict-size', type=int, default=128 * 1024,
                        help='Maximum size of trained dictionary')
    parser.add_argument('--dict-sample-limit', type=int,
                        help='limit how many samples are fed into dictionary '
                             'training')
    parser.add_argument('path', metavar='INPUT', nargs='+')

    args = parser.parse_args()

    # If no compression mode defined, assume discrete.
    if not args.stream and not args.content_dict and not args.discrete_dict:
        args.discrete = True

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

    if args.discrete_dict:
        if args.dict_sample_limit:
            training_chunks = chunks[0:args.dict_sample_limit]
        else:
            training_chunks = chunks

        dict_data = zstd.train_dictionary(args.dict_size, training_chunks)
        print('trained dictionary of size %d (wanted %d)' % (
            len(dict_data), args.dict_size))

    # In discrete mode, each input is compressed independently, possibly
    # with a dictionary.
    if args.discrete:
        zctx = zstd.ZstdCompressor(**opts)
        compressed_discrete = []
        ratios = []
        for chunk in chunks:
            c = zctx.compress(chunk)
            compressed_discrete.append(c)
            ratios.append(float(len(c)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_discrete))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print('discrete compressed size: %d (%.2f%%); smaller: %.2f%%' % (
            compressed_size, ratio, good_ratio))

    # Discrete dict mode is like discrete but trains a dictionary.
    if args.discrete_dict:
        dict_opts = dict(opts)
        dict_opts['dict_data'] = dict_data
        zctx = zstd.ZstdCompressor(**dict_opts)
        compressed_discrete_dict = []
        ratios = []
        for chunk in chunks:
            c = zctx.compress(chunk)
            compressed_discrete_dict.append(c)
            ratios.append(float(len(c)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_discrete_dict))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print('discrete dict compressed size: %d (%.2f%%); smaller: %.2f%%' % (
            compressed_size, ratio, good_ratio))

    # In stream mode the inputs are fed into a streaming compressor and
    # blocks are flushed for each input.
    if args.stream:
        zctx = zstd.ZstdCompressor(**opts)
        compressed_stream = []
        ratios = []
        compressor = zctx.compressobj()
        for chunk in chunks:
            output = compressor.compress(chunk)
            output += compressor.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK)
            compressed_stream.append(output)

        compressed_size = sum(map(len, compressed_stream))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        print('stream compressed size: %d (%.2f%%)' % (compressed_size,
                                                       ratio))

    if args.content_dict:
        compressed_content_dict = []
        ratios = []
        # First chunk is compressed like normal.
        c = zstd.ZstdCompressor(**opts).compress(chunks[0])
        compressed_content_dict.append(c)
        ratios.append(float(len(c)) / float(len(chunks[0])))

        # Subsequent chunks use previous chunk as a dict.
        for i, chunk in enumerate(chunks[1:]):
            d = zstd.ZstdCompressionDict(chunks[i])
            zctx = zstd.ZstdCompressor(dict_data=d, **opts)
            c = zctx.compress(chunk)
            compressed_content_dict.append(c)
            ratios.append(float(len(c)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_content_dict))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print('content dict compressed size: %d (%.2f%%); smaller: %.2f%%' % (
            compressed_size, ratio, good_ratio))

    print('')

    if not args.no_compression:
        if args.discrete:
            bench_discrete_compression(chunks, opts)
        if args.discrete_dict:
            bench_discrete_compression(chunks, dict_opts)
        if args.stream:
            bench_stream_compression(chunks, opts)
        if args.content_dict:
            bench_content_dict_compression(chunks, opts)

        if not args.no_decompression:
            print('')

    if not args.no_decompression:
        if args.discrete:
            bench_discrete_decompression(compressed_discrete, orig_size,
                                         opts)
        if args.discrete_dict:
            bench_discrete_decompression(compressed_discrete_dict,
                                         orig_size, dict_opts)
        if args.stream:
            bench_stream_decompression(compressed_stream, orig_size, opts)
        if args.content_dict:
            bench_content_dict_decompression(compressed_content_dict,
                                             orig_size, opts)
