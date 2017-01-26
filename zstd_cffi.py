# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

"""Python interface to the Zstandard (zstd) compression library."""

from __future__ import absolute_import, unicode_literals

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

# TODO remove since redundant with above.
_CSTREAM_IN_SIZE = lib.ZSTD_CStreamInSize()
_CSTREAM_OUT_SIZE = lib.ZSTD_CStreamOutSize()

new_nonzero = ffi.new_allocator(should_clear_after_alloc=False)


MAX_COMPRESSION_LEVEL = lib.ZSTD_maxCLevel()
FRAME_HEADER = b'\x28\xb5\x2f\xfd'
ZSTD_VERSION = (lib.ZSTD_VERSION_MAJOR, lib.ZSTD_VERSION_MINOR, lib.ZSTD_VERSION_RELEASE)

# Simple constant conversion.
for key in (
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
):
    globals()[key] = getattr(lib, 'ZSTD_%s' % key)

for key, value in {
    'MAGIC_NUMBER': 'ZSTD_MAGICNUMBER',
    'STRATEGY_FAST': 'ZSTD_fast',
    'STRATEGY_DFAST': 'ZSTD_dfast',
    'STRATEGY_GREEDY': 'ZSTD_greedy',
    'STRATEGY_LAZY': 'ZSTD_lazy',
    'STRATEGY_LAZY2': 'ZSTD_lazy2',
    'STRATEGY_BTLAZY2': 'ZSTD_btlazy2',
    'STRATEGY_BTOPT': 'ZSTD_btopt',
}.items():
    globals()[key] = getattr(lib, value)


class ZstdError(Exception):
    pass


class CompressionParameters(object):
    def __init__(self, window_log, chain_log, hash_log, search_log,
                 search_length, target_length, strategy):
        if window_log < WINDOWLOG_MIN or window_log > WINDOWLOG_MAX:
            raise ValueError('invalid window log value')

        if chain_log < CHAINLOG_MIN or chain_log > CHAINLOG_MAX:
            raise ValueError('invalid chain log value')

        if hash_log < HASHLOG_MIN or hash_log > HASHLOG_MAX:
            raise ValueError('invalid hash log value')

        if search_log < SEARCHLOG_MIN or search_log > SEARCHLOG_MAX:
            raise ValueError('invalid search log value')

        if search_length < SEARCHLENGTH_MIN or search_length > SEARCHLENGTH_MAX:
            raise ValueError('invalid search length value')

        if target_length < TARGETLENGTH_MIN or target_length > TARGETLENGTH_MAX:
            raise ValueError('invalid target length value')

        if strategy < STRATEGY_FAST or strategy > STRATEGY_BTOPT:
            raise ValueError('invalid strategy value')

        self.window_log = window_log
        self.chain_log = chain_log
        self.hash_log = hash_log
        self.search_log = search_log
        self.search_length = search_length
        self.target_length = target_length
        self.strategy = strategy

    def __len__(self):
        return 7

    def __getitem__(self, idx):
        if idx == 0:
            return self.window_log
        elif idx == 1:
            return self.chain_log
        elif idx == 2:
            return self.hash_log
        elif idx == 3:
            return self.search_log
        elif idx == 4:
            return self.search_length
        elif idx == 5:
            return self.target_length
        elif idx == 6:
            return self.strategy


def get_compression_parameters(level, source_size=0, dict_size=0):
    params = lib.ZSTD_getCParams(level, source_size, dict_size)
    return CompressionParameters(window_log=params.windowLog,
                                 chain_log=params.chainLog,
                                 hash_log=params.hashLog,
                                 search_log=params.searchLog,
                                 search_length=params.searchLength,
                                 target_length=params.targetLength,
                                 strategy=params.strategy)


class _ZstdCompressionWriter(object):
    def __init__(self, cstream, writer):
        self._cstream = cstream
        self._writer = writer

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if not exc_type and not exc_value and not exc_tb:
            out_buffer = ffi.new('ZSTD_outBuffer *')
            dst_buffer = ffi.new('char[]', _CSTREAM_OUT_SIZE)
            out_buffer.dst = dst_buffer
            out_buffer.size = _CSTREAM_OUT_SIZE
            out_buffer.pos = 0

            while True:
                res = lib.ZSTD_endStream(self._cstream, out_buffer)
                if lib.ZSTD_isError(res):
                    raise Exception('error ending compression stream: %s' %
                                    ffi.string(lib.ZSTD_getErrorName))

                if out_buffer.pos:
                    self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                    out_buffer.pos = 0

                if res == 0:
                    break

        return False

    def write(self, data):
        out_buffer = ffi.new('ZSTD_outBuffer *')
        dst_buffer = ffi.new('char[]', _CSTREAM_OUT_SIZE)
        out_buffer.dst = dst_buffer
        out_buffer.size = _CSTREAM_OUT_SIZE
        out_buffer.pos = 0

        # TODO can we reuse existing memory?
        in_buffer = ffi.new('ZSTD_inBuffer *')
        src_buffer = ffi.from_buffer(data)
        in_buffer.src = src_buffer
        in_buffer.size = len(src_buffer)
        in_buffer.pos = 0
        while in_buffer.pos < in_buffer.size:
            res = lib.ZSTD_compressStream(self._cstream, out_buffer, in_buffer)
            if lib.ZSTD_isError(res):
                raise Exception('zstd compress error: %s' %
                                ffi.string(lib.ZSTD_getErrorName(res)))

            if out_buffer.pos:
                self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                out_buffer.pos = 0


class ZstdCompressor(object):
    def __init__(self, level=3, dict_data=None, compression_params=None,
                 write_checksum=False, write_content_size=False,
                 write_dict_id=True):
        if compression_params:
            raise Exception('compression_params not yet supported')

        if level < 1:
            raise ValueError('level must be greater than 0')
        elif level > lib.ZSTD_maxCLevel():
            raise ValueError('level must be less than %d' % lib.ZSTD_maxCLevel())

        self._compression_level = level
        self._dict_data = dict_data

        self._fparams = ffi.new('ZSTD_frameParameters *')[0]
        self._fparams.checksumFlag = write_checksum
        self._fparams.contentSizeFlag = write_content_size
        self._fparams.noDictIDFlag = not write_dict_id

        self._cctx = ffi.gc(lib.ZSTD_createCCtx(), lib.ZSTD_freeCCtx)

    def compress(self, data, allow_empty=False):
        if len(data) == 0 and self._fparams.contentSizeFlag and not allow_empty:
            raise ValueError('cannot write empty inputs when writing content sizes')

        # TODO use a CDict for performance.
        dict_data = ffi.NULL
        dict_size = 0

        if self._dict_data:
            dict_data = self._dict_data.as_bytes()
            dict_size = len(self._dict_data)

        params = ffi.new('ZSTD_parameters *')[0]
        params.cParams = lib.ZSTD_getCParams(self._compression_level, len(data),
                                             dict_size)
        params.fParams = self._fparams

        dest_size = lib.ZSTD_compressBound(len(data))
        out = new_nonzero('char[]', dest_size)

        result = lib.ZSTD_compress_advanced(self._cctx,
                                            ffi.addressof(out), dest_size,
                                            data, len(data),
                                            dict_data, dict_size,
                                            params)

        if lib.ZSTD_isError(result):
            raise ZstdError('cannot compress: %s' %
                            ffi.string(lib.ZSTD_getErrorName(result)))

        return bytes(ffi.buffer(out, result))

    def copy_stream(self, ifh, ofh, size=0, read_size=_CSTREAM_IN_SIZE,
                    write_size=_CSTREAM_OUT_SIZE):

        if not hasattr(ifh, 'read'):
            raise ValueError('first argument must have a read() method')
        if not hasattr(ofh, 'write'):
            raise ValueError('second argument must have a write() method')

        cstream = self._get_cstream(size)

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

            total_read += len(data)

            src_buffer = ffi.new('char[]', data)
            in_buffer.src = src_buffer
            in_buffer.size = len(data)
            in_buffer.pos = 0

            while in_buffer.pos < in_buffer.size:
                res = lib.ZSTD_compressStream(cstream, out_buffer, in_buffer)
                if lib.ZSTD_isError(res):
                    raise ZstdError('zstd compress error: %s' %
                                    ffi.string(lib.ZSTD_getErrorName(res)))

                if out_buffer.pos:
                    ofh.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                    total_write += out_buffer.pos
                    out_buffer.pos = 0

        # We've finished reading. Flush the compressor.
        while True:
            res = lib.ZSTD_endStream(cstream, out_buffer)
            if lib.ZSTD_isError(res):
                raise ZstdError('error ending compression stream: %s' %
                                ffi.string(lib.ZSTD_getErrorName(res)))

            if out_buffer.pos:
                ofh.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                total_write += out_buffer.pos
                out_buffer.pos = 0

            if res == 0:
                break

        return total_read, total_write

    def write_to(self, writer):
        return _ZstdCompressionWriter(self._get_cstream(0), writer)

    def _get_cstream(self, size):
        cstream = lib.ZSTD_createCStream()
        cstream = ffi.gc(cstream, lib.ZSTD_freeCStream)

        dict_data = ffi.NULL
        dict_size = 0
        if self._dict_data:
            dict_data = self._dict_data.as_bytes()
            dict_size = len(self._dict_data)

        zparams = ffi.new('ZSTD_parameters *')[0]
        zparams.cParams = lib.ZSTD_getCParams(self._compression_level,
                                              size, dict_size)
        zparams.fParams = self._fparams

        res = lib.ZSTD_initCStream_advanced(cstream, dict_data, dict_size, zparams, size)
        if lib.ZSTD_isError(res):
            raise Exception('cannot init CStream: %s' %
                            ffi.string(lib.ZSTD_getErrorName(res)))

        return cstream


class FrameParameters(object):
    def __init__(self, fparams):
        self.content_size = fparams.frameContentSize
        self.window_size = fparams.windowSize
        self.dict_id = fparams.dictID
        self.has_checksum = bool(fparams.checksumFlag)


def get_frame_parameters(data):
    if not isinstance(data, bytes_type):
        raise TypeError('argument must be bytes')

    params = ffi.new('ZSTD_frameParams *')

    result = lib.ZSTD_getFrameParams(params, data, len(data))
    if lib.ZSTD_isError(result):
        raise ZstdError('cannot get frame parameters: %s' %
                        ffi.string(lib.ZSTD_getErrorName(result)))

    if result:
        raise ZstdError('not enough data for frame parameters; need %d bytes' %
                        result)

    return FrameParameters(params[0])


class ZstdCompressionDict(object):
    def __init__(self, data):
        assert isinstance(data, bytes_type)
        self._data = data

    def __len__(self):
        return len(self._data)

    def dict_id(self):
        return int_type(lib.ZDICT_getDictID(self._data, len(self._data)))

    def as_bytes(self):
        return self._data


def train_dictionary(dict_size, samples, parameters=None):
    if not isinstance(samples, list):
        raise TypeError('samples must be a list')

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

    result = lib.ZDICT_trainFromBuffer(ffi.addressof(dict_data), dict_size,
                                       ffi.addressof(samples_buffer),
                                       ffi.addressof(sample_sizes, 0),
                                       len(samples))
    if lib.ZDICT_isError(result):
        raise ZstdError('Cannot train dict: %s' %
                        ffi.string(lib.ZDICT_getErrorName(result)))

    return ZstdCompressionDict(bytes_type(ffi.buffer(dict_data, result)))
