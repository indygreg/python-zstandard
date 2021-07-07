import argparse

CHUNK_SIZE = 8 * 1024 * 1024


def main(args=None):
    arguments = _parser(args)
    _run(arguments)


def _parser(args=None):
    parser = argparse.ArgumentParser(
        prog="zstandard",
        description="Simple cli to use zstandard to de/compress files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("file", help="A filename")
    parser.add_argument(
        "-o",
        "--outfile",
        help="Save to this filename",
    )
    parser.add_argument(
        "-d",
        "--decompress",
        help="Decompress instead of compressing.",
        action="store_true",
    )
    parser.add_argument(
        "-l",
        "--level",
        help="Integer compression level. "
        "Valid values are all negative integers through 22",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--override",
        help="Allow overriding existing output files",
        action="store_true",
    )
    parser.add_argument(
        "--threads",
        help="Number of threads to use to compress data concurrently. "
        "0 disables multi-threaded compression. -1 means all logical CPUs",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--rm",
        help="Remove source file after successful de/compression",
        action="store_true",
    )
    return parser.parse_args(args)


def _check_args(args):
    import pathlib

    file = pathlib.Path(args.file)
    if not file.exists() or not file.is_file():
        raise FileNotFoundError(
            f"File {args.file} does not exits or is not a file"
        )
    if args.outfile is None:
        if args.decompress:
            outfile = file.with_name(file.stem)
        else:
            outfile = file.with_name(f"{file.name}.zst")
    else:
        outfile = pathlib.Path(args.outfile)
    if file.resolve() == outfile.resolve():
        raise NotImplementedError(
            "Overriding the input file is not supported."
            "Please specify another output file"
        )
    if outfile.exists() and not args.override:
        raise FileExistsError(
            f"File {args.outfile} exists. Pass --override to override it"
        )
    return file, outfile


def _run(args):
    import zstandard as zstd

    file, outfile = _check_args(args)

    in_fp, out_fp = None, None
    try:
        if args.decompress:
            in_fp = zstd.open(file, "rb")
            out_fp = open(outfile, "wb")
            operation = "decompressing"
        else:
            in_fp = open(file, "rb")
            ctx = zstd.ZstdCompressor(level=args.level, threads=args.threads)
            out_fp = zstd.open(outfile, "wb", cctx=ctx)
            operation = "compressing"
        tot = 0
        while True:
            data = in_fp.read(CHUNK_SIZE)
            if not data:
                break
            out_fp.write(data)
            tot += len(data)
            print(f"{operation} .. {tot//(1024*1024)} MB", end="\r")
        print(" " * 100, end="\r")

    finally:
        if in_fp is not None:
            in_fp.close()
        if out_fp is not None:
            out_fp.close()

    outsize = outfile.stat().st_size
    if args.decompress:
        print(outfile.name, f": {outsize} bytes")
    else:
        insize = file.stat().st_size or 1
        print(
            args.file,
            f": {outsize/insize*100:.2f}% ({insize} => {outsize} bytes)",
            outfile.name,
        )

    if args.rm:
        file.unlink()
