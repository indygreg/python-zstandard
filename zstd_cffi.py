# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

"""Python interface to the Zstandard (zstd) compression library."""

from __future__ import absolute_import, unicode_literals

# This should match what the C extension exports.
__all__ = [
    #'BufferSegment',
    #'BufferSegments',
    #'BufferWithSegments',
    #'BufferWithSegmentsCollection',
    'CompressionParameters',
    'ZstdCompressionDict',
    'ZstdCompressionParameters',
    'ZstdCompressor',
    'ZstdError',
    'ZstdDecompressor',
    'FrameParameters',
    'estimate_decompression_context_size',
    'frame_content_size',
    'frame_header_size',
    'get_frame_parameters',
    'train_dictionary',

    # Constants.
    'COMPRESSOBJ_FLUSH_FINISH',
    'COMPRESSOBJ_FLUSH_BLOCK',
    'ZSTD_VERSION',
    'FRAME_HEADER',
    'CONTENTSIZE_UNKNOWN',
    'CONTENTSIZE_ERROR',
    'MAX_COMPRESSION_LEVEL',
    'COMPRESSION_RECOMMENDED_INPUT_SIZE',
    'COMPRESSION_RECOMMENDED_OUTPUT_SIZE',
    'DECOMPRESSION_RECOMMENDED_INPUT_SIZE',
    'DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE',
    'MAGIC_NUMBER',
    'BLOCKSIZELOG_MAX',
    'BLOCKSIZE_MAX',
    'WINDOWLOG_MIN',
    'WINDOWLOG_MAX',
    'CHAINLOG_MIN',
    'CHAINLOG_MAX',
    'HASHLOG_MIN',
    'HASHLOG_MAX',
    'HASHLOG3_MAX',
    'SEARCHLOG_MIN',
    'SEARCHLOG_MAX',
    'SEARCHLENGTH_MIN',
    'SEARCHLENGTH_MAX',
    'TARGETLENGTH_MIN',
    'TARGETLENGTH_MAX',
    'LDM_MINMATCH_MIN',
    'LDM_MINMATCH_MAX',
    'LDM_BUCKETSIZELOG_MAX',
    'STRATEGY_FAST',
    'STRATEGY_DFAST',
    'STRATEGY_GREEDY',
    'STRATEGY_LAZY',
    'STRATEGY_LAZY2',
    'STRATEGY_BTLAZY2',
    'STRATEGY_BTOPT',
    'STRATEGY_BTULTRA',
    'DICT_TYPE_AUTO',
    'DICT_TYPE_RAWCONTENT',
    'DICT_TYPE_FULLDICT',
    'FORMAT_ZSTD1',
    'FORMAT_ZSTD1_MAGICLESS',
]

import io
import os
import sys

from _zstd_cffi import (
    ffi,
    lib,
)

if sys.version_info[0] == 2:
    bytes_type = str
    int_type = long
else:
    bytes_type = bytes
    int_type = int


COMPRESSION_RECOMMENDED_INPUT_SIZE = lib.ZSTD_CStreamInSize()
COMPRESSION_RECOMMENDED_OUTPUT_SIZE = lib.ZSTD_CStreamOutSize()
DECOMPRESSION_RECOMMENDED_INPUT_SIZE = lib.ZSTD_DStreamInSize()
DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE = lib.ZSTD_DStreamOutSize()

new_nonzero = ffi.new_allocator(should_clear_after_alloc=False)


MAX_COMPRESSION_LEVEL = lib.ZSTD_maxCLevel()
MAGIC_NUMBER = lib.ZSTD_MAGICNUMBER
FRAME_HEADER = b'\x28\xb5\x2f\xfd'
CONTENTSIZE_UNKNOWN = lib.ZSTD_CONTENTSIZE_UNKNOWN
CONTENTSIZE_ERROR = lib.ZSTD_CONTENTSIZE_ERROR
ZSTD_VERSION = (lib.ZSTD_VERSION_MAJOR, lib.ZSTD_VERSION_MINOR, lib.ZSTD_VERSION_RELEASE)

BLOCKSIZELOG_MAX = lib.ZSTD_BLOCKSIZELOG_MAX
BLOCKSIZE_MAX = lib.ZSTD_BLOCKSIZE_MAX
WINDOWLOG_MIN = lib.ZSTD_WINDOWLOG_MIN
WINDOWLOG_MAX = lib.ZSTD_WINDOWLOG_MAX
CHAINLOG_MIN = lib.ZSTD_CHAINLOG_MIN
CHAINLOG_MAX = lib.ZSTD_CHAINLOG_MAX
HASHLOG_MIN = lib.ZSTD_HASHLOG_MIN
HASHLOG_MAX = lib.ZSTD_HASHLOG_MAX
HASHLOG3_MAX = lib.ZSTD_HASHLOG3_MAX
SEARCHLOG_MIN = lib.ZSTD_SEARCHLOG_MIN
SEARCHLOG_MAX = lib.ZSTD_SEARCHLOG_MAX
SEARCHLENGTH_MIN = lib.ZSTD_SEARCHLENGTH_MIN
SEARCHLENGTH_MAX = lib.ZSTD_SEARCHLENGTH_MAX
TARGETLENGTH_MIN = lib.ZSTD_TARGETLENGTH_MIN
TARGETLENGTH_MAX = lib.ZSTD_TARGETLENGTH_MAX
LDM_MINMATCH_MIN = lib.ZSTD_LDM_MINMATCH_MIN
LDM_MINMATCH_MAX = lib.ZSTD_LDM_MINMATCH_MAX
LDM_BUCKETSIZELOG_MAX = lib.ZSTD_LDM_BUCKETSIZELOG_MAX

STRATEGY_FAST = lib.ZSTD_fast
STRATEGY_DFAST = lib.ZSTD_dfast
STRATEGY_GREEDY = lib.ZSTD_greedy
STRATEGY_LAZY = lib.ZSTD_lazy
STRATEGY_LAZY2 = lib.ZSTD_lazy2
STRATEGY_BTLAZY2 = lib.ZSTD_btlazy2
STRATEGY_BTOPT = lib.ZSTD_btopt
STRATEGY_BTULTRA = lib.ZSTD_btultra

DICT_TYPE_AUTO = lib.ZSTD_dct_auto
DICT_TYPE_RAWCONTENT = lib.ZSTD_dct_rawContent
DICT_TYPE_FULLDICT = lib.ZSTD_dct_fullDict

FORMAT_ZSTD1 = lib.ZSTD_f_zstd1
FORMAT_ZSTD1_MAGICLESS = lib.ZSTD_f_zstd1_magicless

COMPRESSOBJ_FLUSH_FINISH = 0
COMPRESSOBJ_FLUSH_BLOCK = 1


def _cpu_count():
    # os.cpu_count() was introducd in Python 3.4.
    try:
        return os.cpu_count() or 0
    except AttributeError:
        pass

    # Linux.
    try:
        if sys.version_info[0] == 2:
            return os.sysconf(b'SC_NPROCESSORS_ONLN')
        else:
            return os.sysconf(u'SC_NPROCESSORS_ONLN')
    except (AttributeError, ValueError):
        pass

    # TODO implement on other platforms.
    return 0


class ZstdError(Exception):
    pass


def _zstd_error(zresult):
    # Resolves to bytes on Python 2 and 3. We use the string for formatting
    # into error messages, which will be literal unicode. So convert it to
    # unicode.
    return ffi.string(lib.ZSTD_getErrorName(zresult)).decode('utf-8')

def _make_cctx_params(params):
    res = lib.ZSTD_createCCtxParams()
    if res == ffi.NULL:
        raise MemoryError()

    res = ffi.gc(res, lib.ZSTD_freeCCtxParams)

    attrs = [
        (lib.ZSTD_p_format, params.format),
        (lib.ZSTD_p_compressionLevel, params.compression_level),
        (lib.ZSTD_p_windowLog, params.window_log),
        (lib.ZSTD_p_hashLog, params.hash_log),
        (lib.ZSTD_p_chainLog, params.chain_log),
        (lib.ZSTD_p_searchLog, params.search_log),
        (lib.ZSTD_p_minMatch, params.min_match),
        (lib.ZSTD_p_targetLength, params.target_length),
        (lib.ZSTD_p_compressionStrategy, params.compression_strategy),
        (lib.ZSTD_p_contentSizeFlag, params.write_content_size),
        (lib.ZSTD_p_checksumFlag, params.write_checksum),
        (lib.ZSTD_p_dictIDFlag, params.write_dict_id),
        (lib.ZSTD_p_nbWorkers, params.threads),
        (lib.ZSTD_p_jobSize, params.job_size),
        (lib.ZSTD_p_overlapSizeLog, params.overlap_size_log),
        (lib.ZSTD_p_forceMaxWindow, params.force_max_window),
        (lib.ZSTD_p_enableLongDistanceMatching, params.enable_ldm),
        (lib.ZSTD_p_ldmHashLog, params.ldm_hash_log),
        (lib.ZSTD_p_ldmMinMatch, params.ldm_min_match),
        (lib.ZSTD_p_ldmBucketSizeLog, params.ldm_bucket_size_log),
        (lib.ZSTD_p_ldmHashEveryLog, params.ldm_hash_every_log),
    ]

    for param, value in attrs:
        _set_compression_parameter(res, param, value)

    return res

class ZstdCompressionParameters(object):
    @staticmethod
    def from_level(level, source_size=0, dict_size=0, **kwargs):
        params = lib.ZSTD_getCParams(level, source_size, dict_size)

        args = {
            'window_log': 'windowLog',
            'chain_log': 'chainLog',
            'hash_log': 'hashLog',
            'search_log': 'searchLog',
            'min_match': 'searchLength',
            'target_length': 'targetLength',
            'compression_strategy': 'strategy',
        }

        for arg, attr in args.items():
            if arg not in kwargs:
                kwargs[arg] = getattr(params, attr)

        return ZstdCompressionParameters(**kwargs)

    def __init__(self, format=0, compression_level=0, window_log=0, hash_log=0,
                 chain_log=0, search_log=0, min_match=0, target_length=0,
                 compression_strategy=0, write_content_size=1, write_checksum=0,
                 write_dict_id=0, job_size=0, overlap_size_log=0,
                 force_max_window=0, enable_ldm=0, ldm_hash_log=0,
                 ldm_min_match=0, ldm_bucket_size_log=0, ldm_hash_every_log=0,
                 threads=0):

        if threads < 0:
            threads = _cpu_count()

        self.format = format
        self.compression_level = compression_level
        self.window_log = window_log
        self.hash_log = hash_log
        self.chain_log = chain_log
        self.search_log = search_log
        self.min_match = min_match
        self.target_length = target_length
        self.compression_strategy = compression_strategy
        self.write_content_size = write_content_size
        self.write_checksum = write_checksum
        self.write_dict_id = write_dict_id
        self.job_size = job_size
        self.overlap_size_log = overlap_size_log
        self.force_max_window = force_max_window
        self.enable_ldm = enable_ldm
        self.ldm_hash_log = ldm_hash_log
        self.ldm_min_match = ldm_min_match
        self.ldm_bucket_size_log = ldm_bucket_size_log
        self.ldm_hash_every_log = ldm_hash_every_log
        self.threads = threads

        self.params = _make_cctx_params(self)

    def estimated_compression_context_size(self):
        return lib.ZSTD_estimateCCtxSize_usingCCtxParams(self.params)

CompressionParameters = ZstdCompressionParameters

def estimate_decompression_context_size():
    return lib.ZSTD_estimateDCtxSize()


def _set_compression_parameter(params, param, value):
    zresult = lib.ZSTD_CCtxParam_setParameter(params, param,
                                              ffi.cast('unsigned', value))
    if lib.ZSTD_isError(zresult):
        raise ZstdError('unable to set compression context parameter: %s' %
                        _zstd_error(zresult))

class ZstdCompressionWriter(object):
    def __init__(self, compressor, writer, source_size, write_size):
        self._compressor = compressor
        self._writer = writer
        self._source_size = source_size
        self._write_size = write_size
        self._entered = False
        self._bytes_compressed = 0

    def __enter__(self):
        if self._entered:
            raise ZstdError('cannot __enter__ multiple times')

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._compressor._cctx,
                                                  self._source_size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        self._entered = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._entered = False

        if not exc_type and not exc_value and not exc_tb:
            dst_buffer = ffi.new('char[]', self._write_size)

            out_buffer = ffi.new('ZSTD_outBuffer *')
            in_buffer = ffi.new('ZSTD_inBuffer *')

            out_buffer.dst = dst_buffer
            out_buffer.size = len(dst_buffer)
            out_buffer.pos = 0

            in_buffer.src = ffi.NULL
            in_buffer.size = 0
            in_buffer.pos = 0

            while True:
                zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                    out_buffer, in_buffer,
                                                    lib.ZSTD_e_end)

                if lib.ZSTD_isError(zresult):
                    raise ZstdError('error ending compression stream: %s' %
                                    _zstd_error(zresult))

                if out_buffer.pos:
                    self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos)[:])
                    out_buffer.pos = 0

                if zresult == 0:
                    break

        self._compressor = None

        return False

    def memory_size(self):
        if not self._entered:
            raise ZstdError('cannot determine size of an inactive compressor; '
                            'call when a context manager is active')

        return lib.ZSTD_sizeof_CCtx(self._compressor._cctx)

    def write(self, data):
        if not self._entered:
            raise ZstdError('write() must be called from an active context '
                            'manager')

        total_write = 0

        data_buffer = ffi.from_buffer(data)

        in_buffer = ffi.new('ZSTD_inBuffer *')
        in_buffer.src = data_buffer
        in_buffer.size = len(data_buffer)
        in_buffer.pos = 0

        out_buffer = ffi.new('ZSTD_outBuffer *')
        dst_buffer = ffi.new('char[]', self._write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = self._write_size
        out_buffer.pos = 0

        while in_buffer.pos < in_buffer.size:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                out_buffer, in_buffer,
                                                lib.ZSTD_e_continue)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' %
                                _zstd_error(zresult))

            if out_buffer.pos:
                self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos)[:])
                total_write += out_buffer.pos
                self._bytes_compressed += out_buffer.pos
                out_buffer.pos = 0

        return total_write

    def flush(self):
        if not self._entered:
            raise ZstdError('flush must be called from an active context manager')

        total_write = 0

        out_buffer = ffi.new('ZSTD_outBuffer *')
        dst_buffer = ffi.new('char[]', self._write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = self._write_size
        out_buffer.pos = 0

        in_buffer = ffi.new('ZSTD_inBuffer *')
        in_buffer.src = ffi.NULL
        in_buffer.size = 0
        in_buffer.pos = 0

        while True:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                out_buffer, in_buffer,
                                                lib.ZSTD_e_flush)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' %
                                _zstd_error(zresult))

            if out_buffer.pos:
                self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos)[:])
                total_write += out_buffer.pos
                self._bytes_compressed += out_buffer.pos
                out_buffer.pos = 0

            if not zresult:
                break

        return total_write

    def tell(self):
        return self._bytes_compressed


class ZstdCompressionObj(object):
    def compress(self, data):
        if self._finished:
            raise ZstdError('cannot call compress() after compressor finished')

        data_buffer = ffi.from_buffer(data)
        source = ffi.new('ZSTD_inBuffer *')
        source.src = data_buffer
        source.size = len(data_buffer)
        source.pos = 0

        chunks = []

        while source.pos < len(data):
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                self._out,
                                                source,
                                                lib.ZSTD_e_continue)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' %
                                _zstd_error(zresult))

            if self._out.pos:
                chunks.append(ffi.buffer(self._out.dst, self._out.pos)[:])
                self._out.pos = 0

        return b''.join(chunks)

    def flush(self, flush_mode=COMPRESSOBJ_FLUSH_FINISH):
        if flush_mode not in (COMPRESSOBJ_FLUSH_FINISH, COMPRESSOBJ_FLUSH_BLOCK):
            raise ValueError('flush mode not recognized')

        if self._finished:
            raise ZstdError('compressor object already finished')

        if flush_mode == COMPRESSOBJ_FLUSH_BLOCK:
            z_flush_mode = lib.ZSTD_e_flush
        elif flush_mode == COMPRESSOBJ_FLUSH_FINISH:
            z_flush_mode = lib.ZSTD_e_end
            self._finished = True
        else:
            raise ZstdError('unhandled flush mode')

        assert self._out.pos == 0

        in_buffer = ffi.new('ZSTD_inBuffer *')
        in_buffer.src = ffi.NULL
        in_buffer.size = 0
        in_buffer.pos = 0

        chunks = []

        while True:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                self._out,
                                                in_buffer,
                                                z_flush_mode)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('error ending compression stream: %s' %
                                _zstd_error(zresult))

            if self._out.pos:
                chunks.append(ffi.buffer(self._out.dst, self._out.pos)[:])
                self._out.pos = 0

            if not zresult:
                break

        return b''.join(chunks)


class ZstdCompressionChunker(object):
    def __init__(self, compressor, chunk_size):
        self._compressor = compressor
        self._out = ffi.new('ZSTD_outBuffer *')
        self._dst_buffer = ffi.new('char[]', chunk_size)
        self._out.dst = self._dst_buffer
        self._out.size = chunk_size
        self._out.pos = 0

        self._in = ffi.new('ZSTD_inBuffer *')
        self._in.src = ffi.NULL
        self._in.size = 0
        self._in.pos = 0
        self._finished = False

    def compress(self, data):
        if self._finished:
            raise ZstdError('cannot call compress() after compression finished')

        if self._in.src != ffi.NULL:
            raise ZstdError('cannot perform operation before consuming output '
                            'from previous operation')

        data_buffer = ffi.from_buffer(data)

        if not len(data_buffer):
            return

        self._in.src = data_buffer
        self._in.size = len(data_buffer)
        self._in.pos = 0

        while self._in.pos < self._in.size:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                self._out,
                                                self._in,
                                                lib.ZSTD_e_continue)

            if self._in.pos == self._in.size:
                self._in.src = ffi.NULL
                self._in.size = 0
                self._in.pos = 0

            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' %
                                _zstd_error(zresult))

            if self._out.pos == self._out.size:
                yield ffi.buffer(self._out.dst, self._out.pos)[:]
                self._out.pos = 0

    def flush(self):
        if self._finished:
            raise ZstdError('cannot call flush() after compression finished')

        if self._in.src != ffi.NULL:
            raise ZstdError('cannot call flush() before consuming output from '
                            'previous operation')

        while True:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                self._out, self._in,
                                                lib.ZSTD_e_flush)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' % _zstd_error(zresult))

            if self._out.pos:
                yield ffi.buffer(self._out.dst, self._out.pos)[:]
                self._out.pos = 0

            if not zresult:
                return

    def finish(self):
        if self._finished:
            raise ZstdError('cannot call finish() after compression finished')

        if self._in.src != ffi.NULL:
            raise ZstdError('cannot call finish() before consuming output from '
                            'previous operation')

        while True:
            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                self._out, self._in,
                                                lib.ZSTD_e_end)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s' % _zstd_error(zresult))

            if self._out.pos:
                yield ffi.buffer(self._out.dst, self._out.pos)[:]
                self._out.pos = 0

            if not zresult:
                self._finished = True
                return


class CompressionReader(object):
    def __init__(self, compressor, source, read_size):
        self._compressor = compressor
        self._source = source
        self._read_size = read_size
        self._entered = False
        self._closed = False
        self._bytes_compressed = 0
        self._finished_input = False
        self._finished_output = False

        self._in_buffer = ffi.new('ZSTD_inBuffer *')
        # Holds a ref so backing bytes in self._in_buffer stay alive.
        self._source_buffer = None

    def __enter__(self):
        if self._entered:
            raise ValueError('cannot __enter__ multiple times')

        self._entered = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._entered = False
        self._closed = True
        self._source = None
        self._compressor = None

        return False

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    def readline(self):
        raise io.UnsupportedOperation()

    def readlines(self):
        raise io.UnsupportedOperation()

    def write(self, data):
        raise OSError('stream is not writable')

    def writelines(self, ignored):
        raise OSError('stream is not writable')

    def isatty(self):
        return False

    def flush(self):
        return None

    def close(self):
        self._closed = True
        return None

    @property
    def closed(self):
        return self._closed

    def tell(self):
        return self._bytes_compressed

    def readall(self):
        raise NotImplementedError()

    def __iter__(self):
        raise io.UnsupportedOperation()

    def __next__(self):
        raise io.UnsupportedOperation()

    next = __next__

    def read(self, size=-1):
        if self._closed:
            raise ValueError('stream is closed')

        if self._finished_output:
            return b''

        if size < 1:
            raise ValueError('cannot read negative or size 0 amounts')

        # Need a dedicated ref to dest buffer otherwise it gets collected.
        dst_buffer = ffi.new('char[]', size)
        out_buffer = ffi.new('ZSTD_outBuffer *')
        out_buffer.dst = dst_buffer
        out_buffer.size = size
        out_buffer.pos = 0

        def compress_input():
            if self._in_buffer.pos >= self._in_buffer.size:
                return

            old_pos = out_buffer.pos

            zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                                out_buffer, self._in_buffer,
                                                lib.ZSTD_e_continue)

            self._bytes_compressed += out_buffer.pos - old_pos

            if self._in_buffer.pos == self._in_buffer.size:
                self._in_buffer.src = ffi.NULL
                self._in_buffer.pos = 0
                self._in_buffer.size = 0
                self._source_buffer = None

                if not hasattr(self._source, 'read'):
                    self._finished_input = True

            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd compress error: %s',
                                _zstd_error(zresult))

            if out_buffer.pos and out_buffer.pos == out_buffer.size:
                return ffi.buffer(out_buffer.dst, out_buffer.pos)[:]

        def get_input():
            if self._finished_input:
                return

            if hasattr(self._source, 'read'):
                data = self._source.read(self._read_size)

                if not data:
                    self._finished_input = True
                    return

                self._source_buffer = ffi.from_buffer(data)
                self._in_buffer.src = self._source_buffer
                self._in_buffer.size = len(self._source_buffer)
                self._in_buffer.pos = 0
            else:
                self._source_buffer = ffi.from_buffer(self._source)
                self._in_buffer.src = self._source_buffer
                self._in_buffer.size = len(self._source_buffer)
                self._in_buffer.pos = 0

        result = compress_input()
        if result:
            return result

        while not self._finished_input:
            get_input()
            result = compress_input()
            if result:
                return result

        # EOF
        old_pos = out_buffer.pos

        zresult = lib.ZSTD_compress_generic(self._compressor._cctx,
                                            out_buffer, self._in_buffer,
                                            lib.ZSTD_e_end)

        self._bytes_compressed += out_buffer.pos - old_pos

        if lib.ZSTD_isError(zresult):
            raise ZstdError('error ending compression stream: %s',
                            _zstd_error(zresult))

        if zresult == 0:
            self._finished_output = True

        return ffi.buffer(out_buffer.dst, out_buffer.pos)[:]

class ZstdCompressor(object):
    def __init__(self, level=3, dict_data=None, compression_params=None,
                 write_checksum=None, write_content_size=None,
                 write_dict_id=None, threads=0):
        if level > lib.ZSTD_maxCLevel():
            raise ValueError('level must be less than %d' % lib.ZSTD_maxCLevel())

        if threads < 0:
            threads = _cpu_count()

        if compression_params and write_checksum is not None:
            raise ValueError('cannot define compression_params and '
                             'write_checksum')

        if compression_params and write_content_size is not None:
            raise ValueError('cannot define compression_params and '
                             'write_content_size')

        if compression_params and write_dict_id is not None:
            raise ValueError('cannot define compression_params and '
                             'write_dict_id')

        if compression_params and threads:
            raise ValueError('cannot define compression_params and threads')

        if compression_params:
            self._params = _make_cctx_params(compression_params)
        else:
            if write_dict_id is None:
                write_dict_id = True

            params = lib.ZSTD_createCCtxParams()
            if params == ffi.NULL:
                raise MemoryError()

            self._params = ffi.gc(params, lib.ZSTD_freeCCtxParams)

            _set_compression_parameter(self._params,
                                       lib.ZSTD_p_compressionLevel,
                                       level)

            _set_compression_parameter(
                self._params,
                lib.ZSTD_p_contentSizeFlag,
                write_content_size if write_content_size is not None else 1)

            _set_compression_parameter(self._params,
                                       lib.ZSTD_p_checksumFlag,
                                       1 if write_checksum else 0)

            _set_compression_parameter(self._params,
                                       lib.ZSTD_p_dictIDFlag,
                                       1 if write_dict_id else 0)

            if threads:
                _set_compression_parameter(self._params,
                                           lib.ZSTD_p_nbWorkers,
                                           threads)

        cctx = lib.ZSTD_createCCtx()
        if cctx == ffi.NULL:
            raise MemoryError()

        self._cctx = cctx
        self._dict_data = dict_data

        # We defer setting up garbage collection until after calling
        # _setup_cctx() to ensure the memory size estimate is more accurate.
        try:
            self._setup_cctx()
        finally:
            self._cctx = ffi.gc(cctx, lib.ZSTD_freeCCtx,
                                size=lib.ZSTD_sizeof_CCtx(cctx))

    def _setup_cctx(self):
        zresult = lib.ZSTD_CCtx_setParametersUsingCCtxParams(self._cctx,
                                                             self._params)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('could not set compression parameters: %s' %
                            _zstd_error(zresult))

        dict_data = self._dict_data

        if dict_data:
            if dict_data._cdict:
                zresult = lib.ZSTD_CCtx_refCDict(self._cctx, dict_data._cdict)
            else:
                zresult = lib.ZSTD_CCtx_loadDictionary_advanced(
                    self._cctx, dict_data.as_bytes(), len(dict_data),
                    lib.ZSTD_dlm_byRef, dict_data._dict_type)

            if lib.ZSTD_isError(zresult):
                raise ZstdError('could not load compression dictionary: %s' %
                                _zstd_error(zresult))

    def memory_size(self):
        return lib.ZSTD_sizeof_CCtx(self._cctx)

    def compress(self, data):
        lib.ZSTD_CCtx_reset(self._cctx)

        data_buffer = ffi.from_buffer(data)

        dest_size = lib.ZSTD_compressBound(len(data_buffer))
        out = new_nonzero('char[]', dest_size)

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, len(data_buffer))
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        out_buffer = ffi.new('ZSTD_outBuffer *')
        in_buffer = ffi.new('ZSTD_inBuffer *')

        out_buffer.dst = out
        out_buffer.size = dest_size
        out_buffer.pos = 0

        in_buffer.src = data_buffer
        in_buffer.size = len(data_buffer)
        in_buffer.pos = 0

        zresult = lib.ZSTD_compress_generic(self._cctx,
                                            out_buffer,
                                            in_buffer,
                                            lib.ZSTD_e_end)

        if lib.ZSTD_isError(zresult):
            raise ZstdError('cannot compress: %s' %
                            _zstd_error(zresult))
        elif zresult:
            raise ZstdError('unexpected partial frame flush')

        return ffi.buffer(out, out_buffer.pos)[:]

    def compressobj(self, size=-1):
        lib.ZSTD_CCtx_reset(self._cctx)

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        cobj = ZstdCompressionObj()
        cobj._out = ffi.new('ZSTD_outBuffer *')
        cobj._dst_buffer = ffi.new('char[]', COMPRESSION_RECOMMENDED_OUTPUT_SIZE)
        cobj._out.dst = cobj._dst_buffer
        cobj._out.size = COMPRESSION_RECOMMENDED_OUTPUT_SIZE
        cobj._out.pos = 0
        cobj._compressor = self
        cobj._finished = False

        return cobj

    def chunker(self, size=-1, chunk_size=COMPRESSION_RECOMMENDED_OUTPUT_SIZE):
        lib.ZSTD_CCtx_reset(self._cctx)

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        return ZstdCompressionChunker(self, chunk_size=chunk_size)

    def copy_stream(self, ifh, ofh, size=-1,
                    read_size=COMPRESSION_RECOMMENDED_INPUT_SIZE,
                    write_size=COMPRESSION_RECOMMENDED_OUTPUT_SIZE):

        if not hasattr(ifh, 'read'):
            raise ValueError('first argument must have a read() method')
        if not hasattr(ofh, 'write'):
            raise ValueError('second argument must have a write() method')

        lib.ZSTD_CCtx_reset(self._cctx)

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        dst_buffer = ffi.new('char[]', write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = write_size
        out_buffer.pos = 0

        total_read, total_write = 0, 0

        while True:
            data = ifh.read(read_size)
            if not data:
                break

            data_buffer = ffi.from_buffer(data)
            total_read += len(data_buffer)
            in_buffer.src = data_buffer
            in_buffer.size = len(data_buffer)
            in_buffer.pos = 0

            while in_buffer.pos < in_buffer.size:
                zresult = lib.ZSTD_compress_generic(self._cctx,
                                                    out_buffer,
                                                    in_buffer,
                                                    lib.ZSTD_e_continue)
                if lib.ZSTD_isError(zresult):
                    raise ZstdError('zstd compress error: %s' %
                                    _zstd_error(zresult))

                if out_buffer.pos:
                    ofh.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                    total_write += out_buffer.pos
                    out_buffer.pos = 0

        # We've finished reading. Flush the compressor.
        while True:
            zresult = lib.ZSTD_compress_generic(self._cctx,
                                                out_buffer,
                                                in_buffer,
                                                lib.ZSTD_e_end)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('error ending compression stream: %s' %
                                _zstd_error(zresult))

            if out_buffer.pos:
                ofh.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                total_write += out_buffer.pos
                out_buffer.pos = 0

            if zresult == 0:
                break

        return total_read, total_write

    def stream_reader(self, source, size=-1,
                      read_size=COMPRESSION_RECOMMENDED_INPUT_SIZE):
        lib.ZSTD_CCtx_reset(self._cctx)

        try:
            size = len(source)
        except Exception:
            pass

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        return CompressionReader(self, source, read_size)

    def stream_writer(self, writer, size=-1,
                 write_size=COMPRESSION_RECOMMENDED_OUTPUT_SIZE):

        if not hasattr(writer, 'write'):
            raise ValueError('must pass an object with a write() method')

        lib.ZSTD_CCtx_reset(self._cctx)

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        return ZstdCompressionWriter(self, writer, size, write_size)

    write_to = stream_writer

    def read_to_iter(self, reader, size=-1,
                     read_size=COMPRESSION_RECOMMENDED_INPUT_SIZE,
                     write_size=COMPRESSION_RECOMMENDED_OUTPUT_SIZE):
        if hasattr(reader, 'read'):
            have_read = True
        elif hasattr(reader, '__getitem__'):
            have_read = False
            buffer_offset = 0
            size = len(reader)
        else:
            raise ValueError('must pass an object with a read() method or '
                             'conforms to buffer protocol')

        lib.ZSTD_CCtx_reset(self._cctx)

        if size < 0:
            size = lib.ZSTD_CONTENTSIZE_UNKNOWN

        zresult = lib.ZSTD_CCtx_setPledgedSrcSize(self._cctx, size)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('error setting source size: %s' %
                            _zstd_error(zresult))

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        in_buffer.src = ffi.NULL
        in_buffer.size = 0
        in_buffer.pos = 0

        dst_buffer = ffi.new('char[]', write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = write_size
        out_buffer.pos = 0

        while True:
            # We should never have output data sitting around after a previous
            # iteration.
            assert out_buffer.pos == 0

            # Collect input data.
            if have_read:
                read_result = reader.read(read_size)
            else:
                remaining = len(reader) - buffer_offset
                slice_size = min(remaining, read_size)
                read_result = reader[buffer_offset:buffer_offset + slice_size]
                buffer_offset += slice_size

            # No new input data. Break out of the read loop.
            if not read_result:
                break

            # Feed all read data into the compressor and emit output until
            # exhausted.
            read_buffer = ffi.from_buffer(read_result)
            in_buffer.src = read_buffer
            in_buffer.size = len(read_buffer)
            in_buffer.pos = 0

            while in_buffer.pos < in_buffer.size:
                zresult = lib.ZSTD_compress_generic(self._cctx, out_buffer, in_buffer,
                                                    lib.ZSTD_e_continue)
                if lib.ZSTD_isError(zresult):
                    raise ZstdError('zstd compress error: %s' %
                                    _zstd_error(zresult))

                if out_buffer.pos:
                    data = ffi.buffer(out_buffer.dst, out_buffer.pos)[:]
                    out_buffer.pos = 0
                    yield data

            assert out_buffer.pos == 0

            # And repeat the loop to collect more data.
            continue

        # If we get here, input is exhausted. End the stream and emit what
        # remains.
        while True:
            assert out_buffer.pos == 0
            zresult = lib.ZSTD_compress_generic(self._cctx,
                                                out_buffer,
                                                in_buffer,
                                                lib.ZSTD_e_end)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('error ending compression stream: %s' %
                                _zstd_error(zresult))

            if out_buffer.pos:
                data = ffi.buffer(out_buffer.dst, out_buffer.pos)[:]
                out_buffer.pos = 0
                yield data

            if zresult == 0:
                break

    read_from = read_to_iter

    def frame_progression(self):
        progression = lib.ZSTD_getFrameProgression(self._cctx)

        return progression.ingested, progression.consumed, progression.produced


class FrameParameters(object):
    def __init__(self, fparams):
        self.content_size = fparams.frameContentSize
        self.window_size = fparams.windowSize
        self.dict_id = fparams.dictID
        self.has_checksum = bool(fparams.checksumFlag)


def frame_content_size(data):
    data_buffer = ffi.from_buffer(data)

    size = lib.ZSTD_getFrameContentSize(data_buffer, len(data_buffer))

    if size == lib.ZSTD_CONTENTSIZE_ERROR:
        raise ZstdError('error when determining content size')
    elif size == lib.ZSTD_CONTENTSIZE_UNKNOWN:
        return -1
    else:
        return size


def frame_header_size(data):
    data_buffer = ffi.from_buffer(data)

    zresult = lib.ZSTD_frameHeaderSize(data_buffer, len(data_buffer))
    if lib.ZSTD_isError(zresult):
        raise ZstdError('could not determine frame header size: %s' %
                        _zstd_error(zresult))

    return zresult


def get_frame_parameters(data):
    params = ffi.new('ZSTD_frameHeader *')

    data_buffer = ffi.from_buffer(data)
    zresult = lib.ZSTD_getFrameHeader(params, data_buffer, len(data_buffer))
    if lib.ZSTD_isError(zresult):
        raise ZstdError('cannot get frame parameters: %s' %
                        _zstd_error(zresult))

    if zresult:
        raise ZstdError('not enough data for frame parameters; need %d bytes' %
                        zresult)

    return FrameParameters(params[0])


class ZstdCompressionDict(object):
    def __init__(self, data, dict_type=DICT_TYPE_AUTO, k=0, d=0):
        assert isinstance(data, bytes_type)
        self._data = data
        self.k = k
        self.d = d

        if dict_type not in (DICT_TYPE_AUTO, DICT_TYPE_RAWCONTENT,
                             DICT_TYPE_FULLDICT):
            raise ValueError('invalid dictionary load mode: %d; must use '
                             'DICT_TYPE_* constants')

        self._dict_type = dict_type
        self._cdict = None

    def __len__(self):
        return len(self._data)

    def dict_id(self):
        return int_type(lib.ZDICT_getDictID(self._data, len(self._data)))

    def as_bytes(self):
        return self._data

    def precompute_compress(self, level=0, compression_params=None):
        if level and compression_params:
            raise ValueError('must only specify one of level or '
                             'compression_params')

        if not level and not compression_params:
            raise ValueError('must specify one of level or compression_params')

        if level:
            cparams = lib.ZSTD_getCParams(level, 0, len(self._data))
        else:
            cparams = ffi.new('ZSTD_compressionParameters')
            cparams.chainLog = compression_params.chain_log
            cparams.hashLog = compression_params.hash_log
            cparams.searchLength = compression_params.min_match
            cparams.searchLog = compression_params.search_log
            cparams.strategy = compression_params.compression_strategy
            cparams.targetLength = compression_params.target_length
            cparams.windowLog = compression_params.window_log

        cdict = lib.ZSTD_createCDict_advanced(self._data, len(self._data),
                                              lib.ZSTD_dlm_byRef,
                                              self._dict_type,
                                              cparams,
                                              lib.ZSTD_defaultCMem)
        if cdict == ffi.NULL:
            raise ZstdError('unable to precompute dictionary')

        self._cdict = ffi.gc(cdict, lib.ZSTD_freeCDict,
                             size=lib.ZSTD_sizeof_CDict(cdict))

    @property
    def _ddict(self):
        ddict = lib.ZSTD_createDDict_advanced(self._data, len(self._data),
                                              lib.ZSTD_dlm_byRef,
                                              self._dict_type,
                                              lib.ZSTD_defaultCMem)

        if ddict == ffi.NULL:
            raise ZstdError('could not create decompression dict')

        ddict = ffi.gc(ddict, lib.ZSTD_freeDDict,
                       size=lib.ZSTD_sizeof_DDict(ddict))
        self.__dict__['_ddict'] = ddict

        return ddict

def train_dictionary(dict_size, samples, k=0, d=0, notifications=0, dict_id=0,
                     level=0, steps=0, threads=0):
    if not isinstance(samples, list):
        raise TypeError('samples must be a list')

    if threads < 0:
        threads = _cpu_count()

    total_size = sum(map(len, samples))

    samples_buffer = new_nonzero('char[]', total_size)
    sample_sizes = new_nonzero('size_t[]', len(samples))

    offset = 0
    for i, sample in enumerate(samples):
        if not isinstance(sample, bytes_type):
            raise ValueError('samples must be bytes')

        l = len(sample)
        ffi.memmove(samples_buffer + offset, sample, l)
        offset += l
        sample_sizes[i] = l

    dict_data = new_nonzero('char[]', dict_size)

    dparams = ffi.new('ZDICT_cover_params_t *')[0]
    dparams.k = k
    dparams.d = d
    dparams.steps = steps
    dparams.nbThreads = threads
    dparams.zParams.notificationLevel = notifications
    dparams.zParams.dictID = dict_id
    dparams.zParams.compressionLevel = level

    if (not dparams.k and not dparams.d and not dparams.steps
        and not dparams.nbThreads and not dparams.zParams.notificationLevel
        and not dparams.zParams.dictID
        and not dparams.zParams.compressionLevel):
        zresult = lib.ZDICT_trainFromBuffer(
            ffi.addressof(dict_data), dict_size,
            ffi.addressof(samples_buffer),
            ffi.addressof(sample_sizes, 0), len(samples))
    elif dparams.steps or dparams.nbThreads:
        zresult = lib.ZDICT_optimizeTrainFromBuffer_cover(
            ffi.addressof(dict_data), dict_size,
            ffi.addressof(samples_buffer),
            ffi.addressof(sample_sizes, 0), len(samples),
            ffi.addressof(dparams))
    else:
        zresult = lib.ZDICT_trainFromBuffer_cover(
            ffi.addressof(dict_data), dict_size,
            ffi.addressof(samples_buffer),
            ffi.addressof(sample_sizes, 0), len(samples),
            dparams)

    if lib.ZDICT_isError(zresult):
        msg = ffi.string(lib.ZDICT_getErrorName(zresult)).decode('utf-8')
        raise ZstdError('cannot train dict: %s' % msg)

    return ZstdCompressionDict(ffi.buffer(dict_data, zresult)[:],
                               dict_type=DICT_TYPE_FULLDICT,
                               k=dparams.k, d=dparams.d)


class ZstdDecompressionObj(object):
    def __init__(self, decompressor, write_size):
        self._decompressor = decompressor
        self._write_size = write_size
        self._finished = False

    def decompress(self, data):
        if self._finished:
            raise ZstdError('cannot use a decompressobj multiple times')

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        data_buffer = ffi.from_buffer(data)
        in_buffer.src = data_buffer
        in_buffer.size = len(data_buffer)
        in_buffer.pos = 0

        dst_buffer = ffi.new('char[]', self._write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = len(dst_buffer)
        out_buffer.pos = 0

        chunks = []

        while True:
            zresult = lib.ZSTD_decompress_generic(self._decompressor._dctx,
                                                  out_buffer, in_buffer)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd decompressor error: %s' %
                                _zstd_error(zresult))

            if zresult == 0:
                self._finished = True
                self._decompressor = None

            if out_buffer.pos:
                chunks.append(ffi.buffer(out_buffer.dst, out_buffer.pos)[:])

            if (zresult == 0 or
                    (in_buffer.pos == in_buffer.size and out_buffer.pos == 0)):
                break

            out_buffer.pos = 0

        return b''.join(chunks)


class DecompressionReader(object):
    def __init__(self, decompressor, source, read_size):
        self._decompressor = decompressor
        self._source = source
        self._read_size = read_size
        self._entered = False
        self._closed = False
        self._bytes_decompressed = 0
        self._finished_input = False
        self._finished_output = False
        self._in_buffer = ffi.new('ZSTD_inBuffer *')
        # Holds a ref to self._in_buffer.src.
        self._source_buffer = None

    def __enter__(self):
        if self._entered:
            raise ValueError('cannot __enter__ multiple times')

        self._entered = True
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._entered = False
        self._closed = True
        self._source = None
        self._decompressor = None

        return False

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return True

    def readline(self):
        raise NotImplementedError()

    def readlines(self):
        raise NotImplementedError()

    def write(self, data):
        raise io.UnsupportedOperation()

    def writelines(self, lines):
        raise io.UnsupportedOperation()

    def isatty(self):
        return False

    def flush(self):
        return None

    def close(self):
        self._closed = True
        return None

    @property
    def closed(self):
        return self._closed

    def tell(self):
        return self._bytes_decompressed

    def readall(self):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def __next__(self):
        raise NotImplementedError()

    next = __next__

    def read(self, size):
        if self._closed:
            raise ValueError('stream is closed')

        if self._finished_output:
            return b''

        if size < 1:
            raise ValueError('cannot read negative or size 0 amounts')

        dst_buffer = ffi.new('char[]', size)
        out_buffer = ffi.new('ZSTD_outBuffer *')
        out_buffer.dst = dst_buffer
        out_buffer.size = size
        out_buffer.pos = 0

        def decompress():
            zresult = lib.ZSTD_decompress_generic(self._decompressor._dctx,
                                                  out_buffer, self._in_buffer)

            if self._in_buffer.pos == self._in_buffer.size:
                self._in_buffer.src = ffi.NULL
                self._in_buffer.pos = 0
                self._in_buffer.size = 0
                self._source_buffer = None

                if not hasattr(self._source, 'read'):
                    self._finished_input = True

            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd decompress error: %s',
                                _zstd_error(zresult))
            elif zresult == 0:
                self._finished_output = True

            if out_buffer.pos and out_buffer.pos == out_buffer.size:
                self._bytes_decompressed += out_buffer.size
                return ffi.buffer(out_buffer.dst, out_buffer.pos)[:]

        def get_input():
            if self._finished_input:
                return

            if hasattr(self._source, 'read'):
                data = self._source.read(self._read_size)

                if not data:
                    self._finished_input = True
                    return

                self._source_buffer = ffi.from_buffer(data)
                self._in_buffer.src = self._source_buffer
                self._in_buffer.size = len(self._source_buffer)
                self._in_buffer.pos = 0
            else:
                self._source_buffer = ffi.from_buffer(self._source)
                self._in_buffer.src = self._source_buffer
                self._in_buffer.size = len(self._source_buffer)
                self._in_buffer.pos = 0

        get_input()
        result = decompress()
        if result:
            return result

        while not self._finished_input:
            get_input()
            result = decompress()
            if result:
                return result

        self._bytes_decompressed += out_buffer.pos
        return ffi.buffer(out_buffer.dst, out_buffer.pos)[:]

    def seek(self, pos, whence=os.SEEK_SET):
        if self._closed:
            raise ValueError('stream is closed')

        read_amount = 0

        if whence == os.SEEK_SET:
            if pos < 0:
                raise ValueError('cannot seek to negative position with SEEK_SET')

            if pos < self._bytes_decompressed:
                raise ValueError('cannot seek zstd decompression stream '
                                 'backwards')

            read_amount = pos - self._bytes_decompressed

        elif whence == os.SEEK_CUR:
            if pos < 0:
                raise ValueError('cannot seek zstd decompression stream '
                                 'backwards')

            read_amount = pos
        elif whence == os.SEEK_END:
            raise ValueError('zstd decompression streams cannot be seeked '
                             'with SEEK_END')

        while read_amount:
            result = self.read(min(read_amount,
                                   DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE))

            if not result:
                break

            read_amount -= len(result)

        return self._bytes_decompressed

class ZstdDecompressionWriter(object):
    def __init__(self, decompressor, writer, write_size):
        self._decompressor = decompressor
        self._writer = writer
        self._write_size = write_size
        self._entered = False

    def __enter__(self):
        if self._entered:
            raise ZstdError('cannot __enter__ multiple times')

        self._decompressor._ensure_dctx()
        self._entered = True

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._entered = False

    def memory_size(self):
        if not self._decompressor._dctx:
            raise ZstdError('cannot determine size of inactive decompressor '
                            'call when context manager is active')

        return lib.ZSTD_sizeof_DCtx(self._decompressor._dctx)

    def write(self, data):
        if not self._entered:
            raise ZstdError('write must be called from an active context manager')

        total_write = 0

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        data_buffer = ffi.from_buffer(data)
        in_buffer.src = data_buffer
        in_buffer.size = len(data_buffer)
        in_buffer.pos = 0

        dst_buffer = ffi.new('char[]', self._write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = len(dst_buffer)
        out_buffer.pos = 0

        dctx = self._decompressor._dctx

        while in_buffer.pos < in_buffer.size:
            zresult = lib.ZSTD_decompress_generic(dctx, out_buffer, in_buffer)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('zstd decompress error: %s' %
                                _zstd_error(zresult))

            if out_buffer.pos:
                self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos)[:])
                total_write += out_buffer.pos
                out_buffer.pos = 0

        return total_write


class ZstdDecompressor(object):
    def __init__(self, dict_data=None, max_window_size=0, format=FORMAT_ZSTD1):
        self._dict_data = dict_data
        self._max_window_size = max_window_size
        self._format = format

        dctx = lib.ZSTD_createDCtx()
        if dctx == ffi.NULL:
            raise MemoryError()

        self._dctx = dctx

        # Defer setting up garbage collection until full state is loaded so
        # the memory size is more accurate.
        try:
            self._ensure_dctx()
        finally:
            self._dctx = ffi.gc(dctx, lib.ZSTD_freeDCtx,
                                size=lib.ZSTD_sizeof_DCtx(dctx))

    def memory_size(self):
        return lib.ZSTD_sizeof_DCtx(self._dctx)

    def decompress(self, data, max_output_size=0):
        self._ensure_dctx()

        data_buffer = ffi.from_buffer(data)

        output_size = lib.ZSTD_getFrameContentSize(data_buffer, len(data_buffer))

        if output_size == lib.ZSTD_CONTENTSIZE_ERROR:
            raise ZstdError('error determining content size from frame header')
        elif output_size == 0:
            return b''
        elif output_size == lib.ZSTD_CONTENTSIZE_UNKNOWN:
            if not max_output_size:
                raise ZstdError('could not determine content size in frame header')

            result_buffer = ffi.new('char[]', max_output_size)
            result_size = max_output_size
            output_size = 0
        else:
            result_buffer = ffi.new('char[]', output_size)
            result_size = output_size

        out_buffer = ffi.new('ZSTD_outBuffer *')
        out_buffer.dst = result_buffer
        out_buffer.size = result_size
        out_buffer.pos = 0

        in_buffer = ffi.new('ZSTD_inBuffer *')
        in_buffer.src = data_buffer
        in_buffer.size = len(data_buffer)
        in_buffer.pos = 0

        zresult = lib.ZSTD_decompress_generic(self._dctx, out_buffer, in_buffer)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('decompression error: %s' %
                            _zstd_error(zresult))
        elif zresult:
            raise ZstdError('decompression error: did not decompress full frame')
        elif output_size and out_buffer.pos != output_size:
            raise ZstdError('decompression error: decompressed %d bytes; expected %d' %
                            (zresult, output_size))

        return ffi.buffer(result_buffer, out_buffer.pos)[:]

    def stream_reader(self, source, read_size=DECOMPRESSION_RECOMMENDED_INPUT_SIZE):
        self._ensure_dctx()
        return DecompressionReader(self, source, read_size)

    def decompressobj(self, write_size=DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE):
        if write_size < 1:
            raise ValueError('write_size must be positive')

        self._ensure_dctx()
        return ZstdDecompressionObj(self, write_size=write_size)

    def read_to_iter(self, reader, read_size=DECOMPRESSION_RECOMMENDED_INPUT_SIZE,
                     write_size=DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE,
                     skip_bytes=0):
        if skip_bytes >= read_size:
            raise ValueError('skip_bytes must be smaller than read_size')

        if hasattr(reader, 'read'):
            have_read = True
        elif hasattr(reader, '__getitem__'):
            have_read = False
            buffer_offset = 0
            size = len(reader)
        else:
            raise ValueError('must pass an object with a read() method or '
                             'conforms to buffer protocol')

        if skip_bytes:
            if have_read:
                reader.read(skip_bytes)
            else:
                if skip_bytes > size:
                    raise ValueError('skip_bytes larger than first input chunk')

                buffer_offset = skip_bytes

        self._ensure_dctx()

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        dst_buffer = ffi.new('char[]', write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = len(dst_buffer)
        out_buffer.pos = 0

        while True:
            assert out_buffer.pos == 0

            if have_read:
                read_result = reader.read(read_size)
            else:
                remaining = size - buffer_offset
                slice_size = min(remaining, read_size)
                read_result = reader[buffer_offset:buffer_offset + slice_size]
                buffer_offset += slice_size

            # No new input. Break out of read loop.
            if not read_result:
                break

            # Feed all read data into decompressor and emit output until
            # exhausted.
            read_buffer = ffi.from_buffer(read_result)
            in_buffer.src = read_buffer
            in_buffer.size = len(read_buffer)
            in_buffer.pos = 0

            while in_buffer.pos < in_buffer.size:
                assert out_buffer.pos == 0

                zresult = lib.ZSTD_decompress_generic(self._dctx, out_buffer, in_buffer)
                if lib.ZSTD_isError(zresult):
                    raise ZstdError('zstd decompress error: %s' %
                                    _zstd_error(zresult))

                if out_buffer.pos:
                    data = ffi.buffer(out_buffer.dst, out_buffer.pos)[:]
                    out_buffer.pos = 0
                    yield data

                if zresult == 0:
                    return

            # Repeat loop to collect more input data.
            continue

        # If we get here, input is exhausted.

    read_from = read_to_iter

    def stream_writer(self, writer, write_size=DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE):
        if not hasattr(writer, 'write'):
            raise ValueError('must pass an object with a write() method')

        return ZstdDecompressionWriter(self, writer, write_size)

    write_to = stream_writer

    def copy_stream(self, ifh, ofh,
                    read_size=DECOMPRESSION_RECOMMENDED_INPUT_SIZE,
                    write_size=DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE):
        if not hasattr(ifh, 'read'):
            raise ValueError('first argument must have a read() method')
        if not hasattr(ofh, 'write'):
            raise ValueError('second argument must have a write() method')

        self._ensure_dctx()

        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        dst_buffer = ffi.new('char[]', write_size)
        out_buffer.dst = dst_buffer
        out_buffer.size = write_size
        out_buffer.pos = 0

        total_read, total_write = 0, 0

        # Read all available input.
        while True:
            data = ifh.read(read_size)
            if not data:
                break

            data_buffer = ffi.from_buffer(data)
            total_read += len(data_buffer)
            in_buffer.src = data_buffer
            in_buffer.size = len(data_buffer)
            in_buffer.pos = 0

            # Flush all read data to output.
            while in_buffer.pos < in_buffer.size:
                zresult = lib.ZSTD_decompress_generic(self._dctx, out_buffer, in_buffer)
                if lib.ZSTD_isError(zresult):
                    raise ZstdError('zstd decompressor error: %s' %
                                    _zstd_error(zresult))

                if out_buffer.pos:
                    ofh.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                    total_write += out_buffer.pos
                    out_buffer.pos = 0

            # Continue loop to keep reading.

        return total_read, total_write

    def decompress_content_dict_chain(self, frames):
        if not isinstance(frames, list):
            raise TypeError('argument must be a list')

        if not frames:
            raise ValueError('empty input chain')

        # First chunk should not be using a dictionary. We handle it specially.
        chunk = frames[0]
        if not isinstance(chunk, bytes_type):
            raise ValueError('chunk 0 must be bytes')

        # All chunks should be zstd frames and should have content size set.
        chunk_buffer = ffi.from_buffer(chunk)
        params = ffi.new('ZSTD_frameHeader *')
        zresult = lib.ZSTD_getFrameHeader(params, chunk_buffer, len(chunk_buffer))
        if lib.ZSTD_isError(zresult):
            raise ValueError('chunk 0 is not a valid zstd frame')
        elif zresult:
            raise ValueError('chunk 0 is too small to contain a zstd frame')

        if params.frameContentSize == lib.ZSTD_CONTENTSIZE_UNKNOWN:
            raise ValueError('chunk 0 missing content size in frame')

        self._ensure_dctx(load_dict=False)

        last_buffer = ffi.new('char[]', params.frameContentSize)

        out_buffer = ffi.new('ZSTD_outBuffer *')
        out_buffer.dst = last_buffer
        out_buffer.size = len(last_buffer)
        out_buffer.pos = 0

        in_buffer = ffi.new('ZSTD_inBuffer *')
        in_buffer.src = chunk_buffer
        in_buffer.size = len(chunk_buffer)
        in_buffer.pos = 0

        zresult = lib.ZSTD_decompress_generic(self._dctx, out_buffer, in_buffer)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('could not decompress chunk 0: %s' %
                            _zstd_error(zresult))
        elif zresult:
            raise ZstdError('chunk 0 did not decompress full frame')

        # Special case of chain length of 1
        if len(frames) == 1:
            return ffi.buffer(last_buffer, len(last_buffer))[:]

        i = 1
        while i < len(frames):
            chunk = frames[i]
            if not isinstance(chunk, bytes_type):
                raise ValueError('chunk %d must be bytes' % i)

            chunk_buffer = ffi.from_buffer(chunk)
            zresult = lib.ZSTD_getFrameHeader(params, chunk_buffer, len(chunk_buffer))
            if lib.ZSTD_isError(zresult):
                raise ValueError('chunk %d is not a valid zstd frame' % i)
            elif zresult:
                raise ValueError('chunk %d is too small to contain a zstd frame' % i)

            if params.frameContentSize == lib.ZSTD_CONTENTSIZE_UNKNOWN:
                raise ValueError('chunk %d missing content size in frame' % i)

            dest_buffer = ffi.new('char[]', params.frameContentSize)

            out_buffer.dst = dest_buffer
            out_buffer.size = len(dest_buffer)
            out_buffer.pos = 0

            in_buffer.src = chunk_buffer
            in_buffer.size = len(chunk_buffer)
            in_buffer.pos = 0

            zresult = lib.ZSTD_decompress_generic(self._dctx, out_buffer, in_buffer)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('could not decompress chunk %d: %s' %
                                _zstd_error(zresult))
            elif zresult:
                raise ZstdError('chunk %d did not decompress full frame' % i)

            last_buffer = dest_buffer
            i += 1

        return ffi.buffer(last_buffer, len(last_buffer))[:]

    def _ensure_dctx(self, load_dict=True):
        lib.ZSTD_DCtx_reset(self._dctx)

        if self._max_window_size:
            zresult = lib.ZSTD_DCtx_setMaxWindowSize(self._dctx,
                                                     self._max_window_size)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('unable to set max window size: %s' %
                                _zstd_error(zresult))

        zresult = lib.ZSTD_DCtx_setFormat(self._dctx, self._format)
        if lib.ZSTD_isError(zresult):
            raise ZstdError('unable to set decoding format: %s' %
                            _zstd_error(zresult))

        if self._dict_data and load_dict:
            zresult = lib.ZSTD_DCtx_refDDict(self._dctx, self._dict_data._ddict)
            if lib.ZSTD_isError(zresult):
                raise ZstdError('unable to reference prepared dictionary: %s' %
                                _zstd_error(zresult))
