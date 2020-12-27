# Copyright (c) 2017-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

"""Python interface to the Zstandard (zstd) compression library."""

from __future__ import absolute_import, unicode_literals

# This module serves 2 roles:
#
# 1) Export the C or CFFI "backend" through a central module.
# 2) Implement additional functionality built on top of C or CFFI backend.

import builtins
import io
import os
import platform

# Some Python implementations don't support C extensions. That's why we have
# a CFFI implementation in the first place. The code here import one of our
# "backends" then re-exports the symbols from this module. For convenience,
# we support falling back to the CFFI backend if the C extension can't be
# imported. But for performance reasons, we only do this on unknown Python
# implementation. Notably, for CPython we require the C extension by default.
# Because someone will inevitably want special behavior, the behavior is
# configurable via an environment variable. A potentially better way to handle
# this is to import a special ``__importpolicy__`` module or something
# defining a variable and `setup.py` could write the file with whatever
# policy was specified at build time. Until someone needs it, we go with
# the hacky but simple environment variable approach.
_module_policy = os.environ.get("PYTHON_ZSTANDARD_IMPORT_POLICY", "default")

if _module_policy == "default":
    if platform.python_implementation() in ("CPython",):
        from .backend_c import *  # type: ignore

        backend = "cext"
    elif platform.python_implementation() in ("PyPy",):
        from .backend_cffi import *  # type: ignore

        backend = "cffi"
    else:
        try:
            from .backend_c import *

            backend = "cext"
        except ImportError:
            from .backend_cffi import *

            backend = "cffi"
elif _module_policy == "cffi_fallback":
    try:
        from .backend_c import *

        backend = "cext"
    except ImportError:
        from .backend_cffi import *

        backend = "cffi"
elif _module_policy == "rust":
    from .backend_rust import *  # type: ignore

    backend = "rust"
elif _module_policy == "cext":
    from .backend_c import *

    backend = "cext"
elif _module_policy == "cffi":
    from .backend_cffi import *

    backend = "cffi"
else:
    raise ImportError(
        "unknown module import policy: %s; use default, cffi_fallback, "
        "cext, or cffi" % _module_policy
    )

# Keep this in sync with python-zstandard.h.
__version__ = "0.15.0.dev0"

_MODE_CLOSED = 0
_MODE_READ = 1
_MODE_WRITE = 2


def open(
    filename,
    mode="rb",
    cctx=None,
    dctx=None,
    encoding=None,
    errors=None,
    newline=None,
    closefd=None,
):
    """Open a zstd compressed file.

    filename can be a filename (given as a str, bytes, or PathLike
    object) or an existing file object. If the former, the file will
    be opened via `builtins.open()` (the `open()` function in the
    standard library).

    mode can be `rb` for reading (the default), `wb` for writing,
    `xb` for creating exclusively, or `ab` for appending. The text mode
    variants `r`, `wb`, `xb`, and `ab` are also accepted and if used will
    result in an `io.TextIOWrapper` being installed.

    cctx is a ZstdCompressor to use for compression. If not specified
    and opened for writing, a default compressor will be used.

    dctx is a ZstdDecompressor to use for decompression. If not specified
    and opened for reading, a default decompressor will be used.

    encoding, errors, and newline are used when operating in text mode
    and are proxied to io.TextIOWrapper.

    closefd specifies whether to close the passed file object when the
    returned file object is closed. If a file is explicitly opened,
    that handle is always closed when the returned file object is closed:
    this argument only matters when filename is a file object.
    """
    normalized_mode = mode.replace("t", "")

    if normalized_mode in ("r", "rb"):
        dctx = dctx or ZstdDecompressor()
        open_mode = "r"
        raw_open_mode = "rb"
    elif normalized_mode in ("w", "wb", "a", "ab", "x", "xb"):
        cctx = cctx or ZstdCompressor()
        open_mode = "w"
        raw_open_mode = normalized_mode
        if not raw_open_mode.endswith("b"):
            raw_open_mode = raw_open_mode + "b"
    else:
        raise ValueError("Invalid mode: {!r}".format(mode))

    if hasattr(os, "PathLike"):
        types = (str, bytes, os.PathLike)
    else:
        types = (str, bytes)

    if isinstance(filename, types):  # type: ignore
        inner_fh = builtins.open(filename, raw_open_mode)
        closefd = True
    elif hasattr(filename, "read") or hasattr(filename, "write"):
        inner_fh = filename
        closefd = bool(closefd)
    else:
        raise TypeError(
            "filename must be a str, bytes, file or PathLike object"
        )

    if open_mode == "r":
        fh = dctx.stream_reader(inner_fh, closefd=closefd)
    elif open_mode == "w":
        fh = cctx.stream_writer(inner_fh, closefd=closefd)
    else:
        raise RuntimeError("logic error in zstandard.open() handling open mode")

    if "b" not in normalized_mode:
        return io.TextIOWrapper(
            fh, encoding=encoding, errors=errors, newline=newline
        )
    else:
        return fh
