from argparse import Namespace
import contextlib
import io
import os
import pathlib
import sys
import unittest
import tempfile

import zstandard as zstd
from zstandard import cli


@contextlib.contextmanager
def redirect_stdout():
    sys.stdout = io.StringIO()
    yield sys.stdout
    sys.stdout = sys.__stdout__


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.count = 1
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls.tmp_dir = pathlib.Path(cls._tmp_dir.name)

    def tearDown(self):
        for file in self.tmp_dir.iterdir():
            file.unlink()

    @classmethod
    def tearDownClass(cls):
        cls._tmp_dir.__exit__(None, None, None)

    def test_parser_default(self):
        args = cli._parser(["my-file"])
        self.assertEqual(
            args,
            Namespace(
                file="my-file",
                outfile=None,
                decompress=False,
                level=3,
                override=False,
                threads=0,
                rm=False,
            ),
        )

    def test_parser(self):
        args = cli._parser(
            [
                "my-file",
                "-d",
                "-o",
                "out-file",
                "-l",
                "2",
                "--override",
                "--threads",
                "-1",
                "--rm",
            ]
        )
        self.assertEqual(
            args,
            Namespace(
                file="my-file",
                outfile="out-file",
                decompress=True,
                level=2,
                override=True,
                threads=-1,
                rm=True,
            ),
        )

    def make_source_file(self):
        data = os.urandom(2048) * 2
        name = self.tmp_dir / "source.dat"
        name.write_bytes(data)
        return data, name

    def compress(self, data, **kw):
        out = io.BytesIO()
        if kw:
            ctx = zstd.ZstdCompressor(**kw)
        else:
            ctx = None
        with zstd.open(out, "wb", cctx=ctx) as f:
            f.write(data)
        return out.getvalue()

    def _compress_run(self, main_args, compress_args, outfile=None):
        data, name = self.make_source_file()
        with redirect_stdout():
            cli.main([str(name.absolute())] + main_args)

        if not outfile:
            dest = self.tmp_dir / f"{name.name}.zst"
        else:
            dest = self.tmp_dir / outfile
        self.assertTrue(dest.exists())
        self.assertEqual(
            dest.read_bytes(), self.compress(data, **compress_args)
        )
        return data, name

    def test_compress(self):
        self._compress_run([], {})

    def test_compress_level(self):
        self._compress_run(["-l", "7"], dict(level=7))

    def test_compress_thread(self):
        self._compress_run(["--threads", "-1"], {})

    def test_compress_rm(self):
        _, name = self._compress_run(["--rm"], {})
        self.assertFalse(name.exists())

    def test_compress_override(self):
        _, name = self._compress_run([], {})
        self.assertRaises(FileExistsError, lambda: self._compress_run([], {}))
        self._compress_run(["--override"], {})

    def test_compress_not_exist(self):
        name = self.tmp_dir / "unknown_file"
        self.assertRaises(
            FileNotFoundError, lambda: cli.main([str(name.absolute())])
        )

    def test_compress_outfile(self):
        self._compress_run(["-o", str(self.tmp_dir / "output")], {}, "output")

    def test_compress_same_output(self):
        _, name = self.make_source_file()

        def go(dest):
            self.assertRaises(
                NotImplementedError,
                lambda: cli.main([str(name.absolute()), "-o", str(dest)]),
            )

        go(name)
        go(name.parent / ".." / name.parent.name / name.name)

    def make_compressed_file(self):
        data = os.urandom(2048) * 2
        name = self.tmp_dir / "source.dat.zst"
        with zstd.open(name, "wb") as f:
            f.write(data)
        return data, name

    def _decompress_run(self, main_args, outfile=None):
        data, name = self.make_compressed_file()
        with redirect_stdout():
            cli.main([str(name.absolute()), "-d"] + main_args)

        if not outfile:
            dest = self.tmp_dir / name.stem
        else:
            dest = self.tmp_dir / outfile
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_bytes(), data)
        return data, name

    def test_decompress(self):
        self._decompress_run([])

    def test_decompress_rm(self):
        _, name = self._decompress_run(["--rm"])
        self.assertFalse(name.exists())

    def test_decompress_override(self):
        _, name = self._decompress_run([])
        self.assertRaises(FileExistsError, lambda: self._decompress_run([]))
        self._decompress_run(["--override"])

    def test_decompress_not_exist(self):
        name = self.tmp_dir / "unknown_file"
        self.assertRaises(
            FileNotFoundError, lambda: cli.main([str(name.absolute()), "-d"])
        )

    def test_decompress_outfile(self):
        self._decompress_run(["-o", str(self.tmp_dir / "output")], "output")

    def test_decompress_same_output(self):
        _, name = self.make_source_file()

        def go(dest, n=name):
            self.assertRaises(
                NotImplementedError,
                lambda: cli.main([str(n.absolute()), "-d", "-o", str(dest)]),
            )

        go(name)
        go(name.parent / ".." / name.parent.name / name.name)

    def test_decompress_no_ext(self):
        no_ext = self.tmp_dir / "no_ext"
        no_ext.touch()
        self.assertRaises(
            NotImplementedError,
            lambda: cli.main([str(no_ext.absolute()), "-d"]),
        )
