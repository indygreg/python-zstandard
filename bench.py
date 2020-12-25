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
import random
import struct
import time
import zlib


import zstandard as zstd


bio = io.BytesIO


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


BENCHES = []


def bench(
    mode,
    title,
    require_content_size=False,
    simple=False,
    zlib=False,
    threads_arg=False,
    chunks_as_buffer=False,
    decompressed_sizes_arg=False,
    cffi=True,
):
    def wrapper(fn):
        if not fn.__name__.startswith(("compress_", "decompress_")):
            raise ValueError(
                "benchmark function must begin with " "compress_ or decompress_"
            )

        fn.mode = mode
        fn.title = title
        fn.require_content_size = require_content_size
        fn.simple = simple
        fn.zlib = zlib
        fn.threads_arg = threads_arg
        fn.chunks_as_buffer = chunks_as_buffer
        fn.decompressed_sizes_arg = decompressed_sizes_arg
        fn.cffi = cffi

        BENCHES.append(fn)

        return fn

    return wrapper


@bench("discrete", "compress() single use zctx")
def compress_one_use(chunks, zparams):
    for chunk in chunks:
        zctx = zstd.ZstdCompressor(compression_params=zparams)
        zctx.compress(chunk)


@bench("discrete", "compress() reuse zctx", simple=True)
def compress_reuse(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        zctx.compress(chunk)


@bench(
    "discrete",
    "multi_compress_to_buffer() w/ buffer input",
    simple=True,
    threads_arg=True,
    chunks_as_buffer=True,
    cffi=False,
)
def compress_multi_compress_to_buffer_buffer(chunks, zparams, threads):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    zctx.multi_compress_to_buffer(chunks, threads=threads)


@bench(
    "discrete",
    "multi_compress_to_buffer() w/ list input",
    threads_arg=True,
    cffi=False,
)
def compress_multi_compress_to_buffer_list(chunks, zparams, threads):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    zctx.multi_compress_to_buffer(chunks, threads=threads)


@bench("discrete", "stream_reader()")
def compress_stream_reader(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        with zctx.stream_reader(chunk) as reader:
            while reader.read(16384):
                pass


@bench("discrete", "stream_writer()")
def compress_stream_writer(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        b = bio()
        with zctx.stream_writer(b) as compressor:
            compressor.write(chunk)


@bench("discrete", "stream_writer() w/ input size")
def compress_stream_writer_size(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        b = bio()
        with zctx.stream_writer(b, size=len(chunk)) as compressor:
            compressor.write(chunk)


@bench("discrete", "read_to_iter()")
def compress_read_to_iter(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        for d in zctx.read_to_iter(chunk):
            pass


@bench("discrete", "read_to_iter() w/ input size")
def compress_read_to_iter_size(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        for d in zctx.read_to_iter(chunk, size=len(chunk)):
            pass


@bench("discrete", "compressobj()")
def compress_compressobj(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        cobj = zctx.compressobj()
        cobj.compress(chunk)
        cobj.flush()


@bench("discrete", "compressobj() w/ input size")
def compress_compressobj_size(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    for chunk in chunks:
        cobj = zctx.compressobj(size=len(chunk))
        cobj.compress(chunk)
        cobj.flush()


@bench("discrete", "chunker()")
def compress_chunker_discrete(chunks, zparams):
    cctx = zstd.ZstdCompressor(compression_params=zparams)
    for in_chunk in chunks:
        chunker = cctx.chunker()
        for out_chunk in chunker.compress(in_chunk):
            pass
        for out_chunk in chunker.finish():
            pass


@bench("discrete", "chunker() w/ input size")
def compress_chunker_discrete_size(chunks, zparams):
    cctx = zstd.ZstdCompressor(compression_params=zparams)
    for in_chunk in chunks:
        chunker = cctx.chunker(size=len(in_chunk))
        for out_chunk in chunker.compress(in_chunk):
            pass
        for out_chunk in chunker.finish():
            pass


@bench("discrete", "compress()", simple=True, zlib=True)
def compress_zlib_discrete(chunks, opts):
    level = opts["zlib_level"]
    c = zlib.compress
    for chunk in chunks:
        c(chunk, level)


@bench("stream", "compressobj()", simple=True, zlib=True)
def compress_zlib_compressobj(chunks, opts):
    compressor = zlib.compressobj(opts["zlib_level"])
    f = zlib.Z_SYNC_FLUSH
    for chunk in chunks:
        compressor.compress(chunk)
        compressor.flush(f)
    compressor.flush()


@bench("stream", "stream_writer()")
def compress_stream_stream_writer(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    b = bio()
    with zctx.stream_writer(b) as compressor:
        for chunk in chunks:
            compressor.write(chunk)
            compressor.flush()


@bench("stream", "compressobj()", simple=True)
def compress_stream_compressobj(chunks, zparams):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    compressor = zctx.compressobj()
    flush = zstd.COMPRESSOBJ_FLUSH_BLOCK
    for chunk in chunks:
        compressor.compress(chunk)
        compressor.flush(flush)


@bench("stream", "chunker()", simple=True)
def compress_stream_chunker(chunks, zparams):
    cctx = zstd.ZstdCompressor(compression_params=zparams)
    chunker = cctx.chunker()

    for chunk in chunks:
        for c in chunker.compress(chunk):
            pass

    for c in chunker.finish():
        pass


@bench("content-dict", "compress()", simple=True)
def compress_content_dict_compress(chunks, zparams):
    zstd.ZstdCompressor(compression_params=zparams).compress(chunks[0])
    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zstd.ZstdCompressor(dict_data=d, compression_params=zparams).compress(
            chunk
        )


@bench("content-dict", "stream_writer()")
def compress_content_dict_stream_writer(chunks, zparams, use_size=False):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    b = bio()
    with zctx.stream_writer(
        b, size=len(chunks[0]) if use_size else -1
    ) as compressor:
        compressor.write(chunks[0])

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        b = bio()
        zctx = zstd.ZstdCompressor(dict_data=d, compression_params=zparams)
        with zctx.stream_writer(
            b, size=len(chunk) if use_size else -1
        ) as compressor:
            compressor.write(chunk)


@bench("content-dict", "stream_writer() w/ input size")
def compress_content_dict_stream_writer_size(chunks, zparams):
    compress_content_dict_stream_writer(chunks, zparams, use_size=True)


@bench("content-dict", "read_to_iter()")
def compress_content_dict_read_to_iter(chunks, zparams, use_size=False):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    size = len(chunks[0]) if use_size else -1
    for o in zctx.read_to_iter(chunks[0], size=size):
        pass

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zctx = zstd.ZstdCompressor(dict_data=d, compression_params=zparams)
        size = len(chunk) if use_size else -1
        for o in zctx.read_to_iter(chunk, size=size):
            pass


@bench("content-dict", "read_to_iter() w/ input size")
def compress_content_dict_read_to_iter_size(chunks, zparams):
    compress_content_dict_read_to_iter(chunks, zparams, use_size=True)


@bench("content-dict", "compressobj()")
def compress_content_dict_compressobj(chunks, zparams, use_size=False):
    zctx = zstd.ZstdCompressor(compression_params=zparams)
    cobj = zctx.compressobj(size=len(chunks[0]) if use_size else -1)
    cobj.compress(chunks[0])
    cobj.flush()

    for i, chunk in enumerate(chunks[1:]):
        d = zstd.ZstdCompressionDict(chunks[i])
        zctx = zstd.ZstdCompressor(dict_data=d, compression_params=zparams)
        cobj = zctx.compressobj(len(chunk) if use_size else -1)
        cobj.compress(chunk)
        cobj.flush()


@bench("content-dict", "compressobj() w/ input size")
def compress_content_dict_compressobj_size(chunks, zparams):
    compress_content_dict_compressobj(chunks, zparams, use_size=True)


@bench("discrete", "decompress() single use zctx", require_content_size=True)
def decompress_one_use(chunks, opts):
    for chunk in chunks:
        zctx = zstd.ZstdDecompressor(**opts)
        zctx.decompress(chunk)


@bench(
    "discrete",
    "decompress() reuse zctx",
    require_content_size=True,
    simple=True,
)
def decompress_reuse(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        zctx.decompress(chunk)


@bench("discrete", "decompress()", simple=True, zlib=True)
def decompress_zlib_decompress(chunks):
    d = zlib.decompress
    for chunk in chunks:
        d(chunk)


@bench(
    "discrete",
    "multi_decompress_to_buffer() w/ buffer input + sizes",
    simple=True,
    threads_arg=True,
    decompressed_sizes_arg=True,
    chunks_as_buffer=True,
    cffi=False,
)
def decompress_multi_decompress_to_buffer_buffer_and_size(
    chunks, opts, threads, decompressed_sizes
):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.multi_decompress_to_buffer(
        chunks, decompressed_sizes=decompressed_sizes, threads=threads
    )


@bench(
    "discrete",
    "multi_decompress_to_buffer() w/ buffer input",
    require_content_size=True,
    threads_arg=True,
    chunks_as_buffer=True,
    cffi=False,
)
def decompress_multi_decompress_to_buffer_buffer(chunks, opts, threads):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.multi_decompress_to_buffer(chunks, threads=threads)


@bench(
    "discrete",
    "multi_decompress_to_buffer() w/ list of bytes input + sizes",
    threads_arg=True,
    decompressed_sizes_arg=True,
    cffi=False,
)
def decompress_multi_decompress_to_buffer_list_and_sizes(
    chunks, opts, threads, decompressed_sizes
):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.multi_decompress_to_buffer(
        chunks, decompressed_sizes=decompressed_sizes, threads=threads
    )


@bench(
    "discrete",
    "multi_decompress_to_buffer() w/ list of bytes input",
    require_content_size=True,
    threads_arg=True,
    cffi=False,
)
def decompress_multi_decompress_to_buffer_list(chunks, opts, threads):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.multi_decompress_to_buffer(chunks, threads=threads)


@bench("discrete", "stream_reader()")
def decompress_stream_reader(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        with zctx.stream_reader(chunk) as reader:
            while reader.read(16384):
                pass


@bench("discrete", "stream_writer()")
def decompress_stream_writer(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        with zctx.stream_writer(bio()) as decompressor:
            decompressor.write(chunk)


@bench("discrete", "read_to_iter()")
def decompress_read_to_iter(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        for d in zctx.read_to_iter(chunk):
            pass


@bench("discrete", "decompressobj()")
def decompress_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    for chunk in chunks:
        decompressor = zctx.decompressobj()
        decompressor.decompress(chunk)


@bench("stream", "decompressobj()", simple=True, zlib=True)
def decompress_zlib_stream(chunks):
    dobj = zlib.decompressobj()
    for chunk in chunks:
        dobj.decompress(chunk)
    dobj.flush()


@bench("stream", "stream_writer()")
def decompress_stream_stream_writer(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    with zctx.stream_writer(bio()) as decompressor:
        for chunk in chunks:
            decompressor.write(chunk)


@bench("stream", "decompressobj()", simple=True)
def decompress_stream_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    decompressor = zctx.decompressobj()
    for chunk in chunks:
        decompressor.decompress(chunk)


@bench("content-dict", "decompress()", require_content_size=True)
def decompress_content_dict_decompress(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = zctx.decompress(chunks[0])

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = zctx.decompress(chunk)


@bench("content-dict", "stream_writer()")
def decompress_content_dict_stream_writer(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    b = bio()
    with zctx.stream_writer(b) as decompressor:
        decompressor.write(chunks[0])

    last = b.getvalue()
    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        b = bio()
        with zctx.stream_writer(b) as decompressor:
            decompressor.write(chunk)
            last = b.getvalue()


@bench("content-dict", "read_to_iter()")
def decompress_content_dict_read_to_iter(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = b"".join(zctx.read_to_iter(chunks[0]))

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = b"".join(zctx.read_to_iter(chunk))


@bench("content-dict", "decompressobj()")
def decompress_content_dict_decompressobj(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    last = zctx.decompressobj().decompress(chunks[0])

    for chunk in chunks[1:]:
        d = zstd.ZstdCompressionDict(last)
        zctx = zstd.ZstdDecompressor(dict_data=d, **opts)
        last = zctx.decompressobj().decompress(chunk)


@bench("content-dict", "decompress_content_dict_chain()", simple=True)
def decompress_content_dict_chain_api(chunks, opts):
    zctx = zstd.ZstdDecompressor(**opts)
    zctx.decompress_content_dict_chain(chunks)


def get_chunks(paths, limit_count, encoding, chunk_size=None):
    chunks = []

    def process_file(p):
        with open(p, "rb") as fh:
            data = fh.read()
            if not data:
                return

            if encoding == "raw":
                pass
            elif encoding == "zlib":
                data = zlib.decompress(data)
            else:
                raise Exception("unexpected chunk encoding: %s" % encoding)

            if chunk_size is not None:
                chunks.extend(
                    [
                        data[i : i + chunk_size]
                        for i in range(0, len(data), chunk_size)
                    ]
                )
            else:
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


def get_benches(mode, direction, zlib=False):
    assert direction in ("compress", "decompress")
    prefix = "%s_" % direction

    fns = []

    for fn in BENCHES:
        if not fn.__name__.startswith(prefix):
            continue

        if fn.mode != mode:
            continue

        if fn.zlib != zlib:
            continue

        if zstd.backend == "cffi" and not fn.cffi:
            continue

        fns.append(fn)

    return fns


def format_results(results, title, prefix, total_size):
    best = min(results)
    rate = float(total_size) / best[3]

    print("%s %s" % (prefix, title))
    print(
        "%.6f wall; %.6f CPU; %.6f user; %.6f sys %.2f MB/s (best of %d)"
        % (best[3], best[0], best[1], best[2], rate / 1000000.0, len(results))
    )


def bench_discrete_zlib_compression(chunks, opts):
    total_size = sum(map(len, chunks))

    for fn in get_benches("discrete", "compress", zlib=True):
        results = timer(lambda: fn(chunks, opts))
        format_results(results, fn.title, "compress discrete zlib", total_size)


def bench_discrete_zlib_decompression(chunks, total_size):
    for fn in get_benches("discrete", "decompress", zlib=True):
        results = timer(lambda: fn(chunks))
        format_results(
            results, fn.title, "decompress discrete zlib", total_size
        )


def bench_discrete_compression(
    chunks, zparams, cover=False, dict_data=None, batch_threads=None
):
    total_size = sum(map(len, chunks))

    if dict_data:
        if cover:
            prefix = "compress discrete cover dict"
        else:
            prefix = "compress discrete dict"
    else:
        prefix = "compress discrete"

    for fn in get_benches("discrete", "compress"):
        chunks_arg = chunks

        kwargs = {}
        if fn.threads_arg:
            kwargs["threads"] = batch_threads

        if fn.chunks_as_buffer:
            s = struct.Struct("=QQ")
            offsets = io.BytesIO()
            current_offset = 0
            for chunk in chunks:
                offsets.write(s.pack(current_offset, len(chunk)))
                current_offset += len(chunk)

            chunks_arg = zstd.BufferWithSegments(
                b"".join(chunks), offsets.getvalue()
            )

        results = timer(lambda: fn(chunks_arg, zparams, **kwargs))
        format_results(results, fn.title, prefix, total_size)


def bench_discrete_decompression(
    orig_chunks,
    compressed_chunks,
    total_size,
    zparams,
    dict_data=None,
    batch_threads=None,
):
    dopts = {}
    if dict_data:
        dopts["dict_data"] = dict_data
        prefix = "decompress discrete dict"
    else:
        prefix = "decompress discrete"

    for fn in get_benches("discrete", "decompress"):
        if not zparams.write_content_size and fn.require_content_size:
            continue

        chunks_arg = compressed_chunks

        kwargs = {}
        if fn.threads_arg:
            kwargs["threads"] = batch_threads

        # Pass compressed frames in a BufferWithSegments rather than a list
        # of bytes.
        if fn.chunks_as_buffer:
            s = struct.Struct("=QQ")
            offsets = io.BytesIO()
            current_offset = 0
            for chunk in compressed_chunks:
                offsets.write(s.pack(current_offset, len(chunk)))
                current_offset += len(chunk)

            chunks_arg = zstd.BufferWithSegments(
                b"".join(compressed_chunks), offsets.getvalue()
            )

        if fn.decompressed_sizes_arg:
            # Ideally we'd use array.array here. But Python 2 doesn't support the
            # Q format.
            s = struct.Struct("=Q")
            kwargs["decompressed_sizes"] = b"".join(
                s.pack(len(c)) for c in orig_chunks
            )

        results = timer(lambda: fn(chunks_arg, dopts, **kwargs))
        format_results(results, fn.title, prefix, total_size)


def bench_stream_compression(chunks, zparams):
    total_size = sum(map(len, chunks))

    for fn in get_benches("stream", "compress"):
        results = timer(lambda: fn(chunks, zparams))
        format_results(results, fn.title, "compress stream", total_size)


def bench_stream_decompression(chunks, total_size):
    for fn in get_benches("stream", "decompress"):
        results = timer(lambda: fn(chunks, {}))
        format_results(results, fn.title, "decompress stream", total_size)


def bench_stream_zlib_compression(chunks, opts):
    total_size = sum(map(len, chunks))

    for fn in get_benches("stream", "compress", zlib=True):
        results = timer(lambda: fn(chunks, opts))
        format_results(results, fn.title, "compress stream zlib", total_size)


def bench_stream_zlib_decompression(chunks, total_size):
    for fn in get_benches("stream", "decompress", zlib=True):
        results = timer(lambda: fn(chunks))
        format_results(results, fn.title, "decompress stream zlib", total_size)


def bench_content_dict_compression(chunks, zparams):
    total_size = sum(map(len, chunks))

    for fn in get_benches("content-dict", "compress"):
        results = timer(lambda: fn(chunks, zparams))
        format_results(results, fn.title, "compress content dict", total_size)


def bench_content_dict_decompression(chunks, total_size, zparams):
    for fn in get_benches("content-dict", "decompress"):
        if not zparams.write_content_size and fn.require_content_size:
            continue

        results = timer(lambda: fn(chunks, {}))
        format_results(results, fn.title, "decompress content dict", total_size)


if __name__ == "__main__":
    import argparse

    random.seed(42)

    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("Compression Modes")
    group.add_argument(
        "--discrete",
        action="store_true",
        help="Compress each input independently",
    )
    group.add_argument(
        "--stream",
        action="store_true",
        help="Feed each input into a stream and emit " "flushed blocks",
    )
    group.add_argument(
        "--content-dict",
        action="store_true",
        help="Compress each input using the previous as a "
        "content dictionary",
    )
    group.add_argument(
        "--discrete-dict",
        action="store_true",
        help="Compress each input independently with a " "dictionary",
    )

    group = parser.add_argument_group("Benchmark Selection")
    group.add_argument(
        "--no-compression",
        action="store_true",
        help="Do not test compression performance",
    )
    group.add_argument(
        "--no-decompression",
        action="store_true",
        help="Do not test decompression performance",
    )
    group.add_argument(
        "--only-simple", action="store_true", help="Only run the simple APIs"
    )
    group.add_argument(
        "--zlib", action="store_true", help="Benchmark against zlib"
    )

    group = parser.add_argument_group("Compression Parameters")
    group.add_argument(
        "-l", "--level", type=int, default=3, help="Compression level"
    )
    group.add_argument(
        "--no-write-size",
        action="store_true",
        help="Do not write content size to zstd frames",
    )
    group.add_argument(
        "--write-checksum",
        action="store_true",
        help="Write checksum data to zstd frames",
    )
    group.add_argument(
        "--dict-size",
        type=int,
        default=128 * 1024,
        help="Maximum size of trained dictionary",
    )
    group.add_argument(
        "--enable-ldm",
        action="store_true",
        help="Enable long distance matching",
    )
    group.add_argument(
        "--ldm-hash-log",
        type=int,
        help="Long distance matching hash log value. Power of 2",
    )
    group.add_argument(
        "--compress-threads",
        type=int,
        help="Use multi-threaded compression with this many " "threads",
    )
    group.add_argument(
        "--batch-threads",
        type=int,
        default=0,
        help="Use this many threads for batch APIs",
    )
    group.add_argument(
        "--cover-k",
        type=int,
        default=0,
        help="Segment size parameter to COVER algorithm",
    )
    group.add_argument(
        "--cover-d",
        type=int,
        default=0,
        help="Dmer size parameter to COVER algorithm",
    )
    group.add_argument(
        "--zlib-level", type=int, default=6, help="zlib compression level"
    )

    group = parser.add_argument_group("Input Processing")
    group.add_argument(
        "--limit-count", type=int, help="limit number of input files added"
    )
    group.add_argument(
        "--dict-sample-limit",
        type=int,
        help="limit how many samples are fed into dictionary " "training",
    )
    group.add_argument(
        "--chunk-encoding",
        choices=["raw", "zlib"],
        default="raw",
        help="How input chunks are encoded. Can be used to "
        "pass compressed chunks for benchmarking",
    )
    group.add_argument(
        "--split-input-size",
        type=int,
        help="Split inputs into chunks so they are at most this " "many bytes",
    )

    parser.add_argument("path", metavar="PATH", nargs="+")

    args = parser.parse_args()

    # If no compression mode defined, assume discrete.
    if not args.stream and not args.content_dict and not args.discrete_dict:
        args.discrete = True

    # It is easier to filter here than to pass arguments to multiple
    # functions.
    if args.only_simple:
        BENCHES[:] = [fn for fn in BENCHES if fn.simple]

    params = {
        "write_content_size": True,
    }
    if args.no_write_size:
        params["write_content_size"] = False
    if args.write_checksum:
        params["write_checksum"] = True
    if args.compress_threads:
        params["threads"] = args.compress_threads
    if args.enable_ldm:
        params["enable_ldm"] = True
    if args.ldm_hash_log:
        params["ldm_hash_log"] = args.ldm_hash_log

    zparams = zstd.ZstdCompressionParameters.from_level(args.level, **params)
    if args.compress_threads:
        threads_zparams = zstd.ZstdCompressionParameters.from_level(
            args.level, **params
        )

    chunks = get_chunks(
        args.path,
        args.limit_count,
        args.chunk_encoding,
        chunk_size=args.split_input_size,
    )
    orig_size = sum(map(len, chunks))
    print("%d chunks; %d bytes" % (len(chunks), orig_size))

    if args.discrete_dict:
        if args.dict_sample_limit:
            training_chunks = random.sample(chunks, args.dict_sample_limit)
        else:
            training_chunks = chunks

        train_args = {
            "level": args.level,
        }

        if args.cover_k:
            train_args["k"] = args.cover_k
        if args.cover_d:
            train_args["d"] = args.cover_d

        # Always use all available threads in optimize mode.
        train_args["threads"] = -1

        dict_data = zstd.train_dictionary(
            args.dict_size, training_chunks, **train_args
        )
        print(
            "trained dictionary of size %d (wanted %d) (l=%d)"
            % (len(dict_data), args.dict_size, args.level)
        )

    if args.zlib and args.discrete:
        compressed_discrete_zlib = []
        ratios = []
        for chunk in chunks:
            c = zlib.compress(chunk, args.zlib_level)
            compressed_discrete_zlib.append(c)
            ratios.append(float(len(c)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_discrete_zlib))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print(
            "zlib discrete compressed size (l=%d): %d (%.2f%%); smaller: %.2f%%"
            % (args.zlib_level, compressed_size, ratio, good_ratio)
        )

    # In discrete mode, each input is compressed independently, possibly
    # with a dictionary.
    if args.discrete:
        zctx = zstd.ZstdCompressor(compression_params=zparams)
        compressed_discrete = []
        ratios = []
        # Always use multiple threads here so we complete faster.
        if hasattr(zctx, "multi_compress_to_buffer"):
            for i, c in enumerate(
                zctx.multi_compress_to_buffer(chunks, threads=-1)
            ):
                compressed_discrete.append(c.tobytes())
                ratios.append(float(len(c)) / float(len(chunks[i])))
        else:
            for chunk in chunks:
                compressed = zctx.compress(chunk)
                compressed_discrete.append(chunk)
                ratios.append(float(len(compressed)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_discrete))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print(
            "discrete compressed size (l=%d): %d (%.2f%%); smaller: %.2f%%"
            % (args.level, compressed_size, ratio, good_ratio)
        )

    # Discrete dict mode is like discrete but trains a dictionary.
    if args.discrete_dict:
        zctx = zstd.ZstdCompressor(
            dict_data=dict_data, compression_params=zparams
        )
        compressed_discrete_dict = []
        ratios = []

        if hasattr(zctx, "multi_compress_to_buffer"):
            for i, c in enumerate(
                zctx.multi_compress_to_buffer(chunks, threads=-1)
            ):
                compressed_discrete_dict.append(c.tobytes())
                ratios.append(float(len(c)) / float(len(chunks[i])))
        else:
            for chunk in chunks:
                compressed = zctx.compress(chunk)
                compressed_discrete_dict.append(compressed)
                ratios.append(float(len(compressed)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_discrete_dict))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print(
            "discrete dict compressed size (l=%d): %d (%.2f%%); smaller: %.2f%%"
            % (args.level, compressed_size, ratio, good_ratio)
        )

    # In stream mode the inputs are fed into a streaming compressor and
    # blocks are flushed for each input.

    if args.zlib and args.stream:
        compressed_stream_zlib = []
        ratios = []
        compressor = zlib.compressobj(args.zlib_level)
        for chunk in chunks:
            output = compressor.compress(chunk)
            output += compressor.flush(zlib.Z_SYNC_FLUSH)
            compressed_stream_zlib.append(output)

        compressed_size = sum(map(len, compressed_stream_zlib))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        print(
            "stream zlib compressed size (l=%d): %d (%.2f%%)"
            % (args.zlib_level, compressed_size, ratio)
        )

    if args.stream:
        zctx = zstd.ZstdCompressor(compression_params=zparams)
        compressed_stream = []
        ratios = []
        compressor = zctx.compressobj()
        for chunk in chunks:
            output = compressor.compress(chunk)
            output += compressor.flush(zstd.COMPRESSOBJ_FLUSH_BLOCK)
            compressed_stream.append(output)

        compressed_size = sum(map(len, compressed_stream))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        print(
            "stream compressed size (l=%d): %d (%.2f%%)"
            % (zparams.compression_level, compressed_size, ratio)
        )

    if args.content_dict:
        compressed_content_dict = []
        ratios = []
        # First chunk is compressed like normal.
        c = zstd.ZstdCompressor(compression_params=zparams).compress(chunks[0])
        compressed_content_dict.append(c)
        ratios.append(float(len(c)) / float(len(chunks[0])))

        # Subsequent chunks use previous chunk as a dict.
        for i, chunk in enumerate(chunks[1:]):
            d = zstd.ZstdCompressionDict(chunks[i])
            zctx = zstd.ZstdCompressor(dict_data=d, compression_params=zparams)
            c = zctx.compress(chunk)
            compressed_content_dict.append(c)
            ratios.append(float(len(c)) / float(len(chunk)))

        compressed_size = sum(map(len, compressed_content_dict))
        ratio = float(compressed_size) / float(orig_size) * 100.0
        bad_count = sum(1 for r in ratios if r >= 1.00)
        good_ratio = 100.0 - (float(bad_count) / float(len(chunks)) * 100.0)
        print(
            "content dict compressed size (l=%d): %d (%.2f%%); smaller: %.2f%%"
            % (zparams.compression_level, compressed_size, ratio, good_ratio)
        )

    print("")

    if not args.no_compression:
        if args.zlib and args.discrete:
            bench_discrete_zlib_compression(
                chunks, {"zlib_level": args.zlib_level}
            )
        if args.discrete:
            bench_discrete_compression(
                chunks, zparams, batch_threads=args.batch_threads
            )
        if args.discrete_dict:
            bench_discrete_compression(
                chunks,
                zparams,
                batch_threads=args.batch_threads,
                dict_data=dict_data,
            )
        if args.zlib and args.stream:
            bench_stream_zlib_compression(
                chunks, {"zlib_level": args.zlib_level}
            )
        if args.stream:
            bench_stream_compression(chunks, zparams)
        if args.content_dict:
            bench_content_dict_compression(chunks, zparams)

        if not args.no_decompression:
            print("")

    if not args.no_decompression:
        if args.zlib and args.discrete:
            bench_discrete_zlib_decompression(
                compressed_discrete_zlib, orig_size
            )
        if args.discrete:
            bench_discrete_decompression(
                chunks,
                compressed_discrete,
                orig_size,
                zparams,
                batch_threads=args.batch_threads,
            )
        if args.discrete_dict:
            bench_discrete_decompression(
                chunks,
                compressed_discrete_dict,
                orig_size,
                zparams,
                dict_data=dict_data,
                batch_threads=args.batch_threads,
            )
        if args.zlib and args.stream:
            bench_stream_zlib_decompression(compressed_stream_zlib, orig_size)
        if args.stream:
            bench_stream_decompression(compressed_stream, orig_size)
        if args.content_dict:
            bench_content_dict_decompression(
                compressed_content_dict, orig_size, zparams
            )
