# Copyright (c) 2016-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

"""Python interface to the Zstandard (zstd) compression library."""

from __future__ import absolute_import, unicode_literals

from _zstd_cffi import (
    ffi,
    lib,
)


_CSTREAM_IN_SIZE = lib.ZSTD_CStreamInSize()
_CSTREAM_OUT_SIZE = lib.ZSTD_CStreamOutSize()


class compresswriter(object):
    def __init__(self, writer, compression_level=3, dict_data=None, compression_params=None):
        if dict_data:
            raise Exception('dict_data not yet supported')
        if compression_params:
            raise Exception('compression_params not yet supported')

        self._writer = writer
        self._compression_level = 3
        self._cstream = None

    def __enter__(self):
        cstream = lib.ZSTD_createCStream()
        self._cstream = ffi.gc(cstream, lib.ZSTD_freeCStream)

        res = lib.ZSTD_initCStream(self._cstream, self._compression_level)
        if lib.ZSTD_isError(res):
            raise Exception('cannot init CStream: %s' % lib.ZSTD_getErrorName())

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if not exc_type and not exc_value and not exc_tb:
            out_buffer = ffi.new('ZSTD_outBuffer *')
            out_buffer.dst = ffi.new('char[]', _CSTREAM_OUT_SIZE)
            out_buffer.size = _CSTREAM_OUT_SIZE
            out_buffer.pos = 0

            while True:
                res = lib.ZSTD_endStream(self._cstream, out_buffer)
                if lib.ZSTD_isError(res):
                    raise Exception('error ending compression stream: %s' % lib.ZSTD_getErrorName)

                if out_buffer.pos:
                    self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                    out_buffer.pos = 0

                if res == 0:
                    break

        return False

    def compress(self, data):
        in_buffer = ffi.new('ZSTD_inBuffer *')
        out_buffer = ffi.new('ZSTD_outBuffer *')

        # TODO can we reuse existing memory?
        in_buffer.src = ffi.new('char[]', data)
        in_buffer.size = len(data)
        in_buffer.pos = 0

        out_buffer.dst = ffi.new('char[]', _CSTREAM_OUT_SIZE)
        out_buffer.size = _CSTREAM_OUT_SIZE
        out_buffer.pos = 0

        while in_buffer.pos < in_buffer.size:
            res = lib.ZSTD_compressStream(self._cstream, out_buffer, in_buffer)
            if lib.ZSTD_isError(res):
                raise Exception('zstd compress error: %s' % lib.ZSTD_getErrorName())

            if out_buffer.pos:
                self._writer.write(ffi.buffer(out_buffer.dst, out_buffer.pos))
                out_buffer.pos = 0
