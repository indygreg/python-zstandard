import imp
import inspect
import io
import os
import types
import unittest

try:
    import hypothesis
except ImportError:
    hypothesis = None


class TestCase(unittest.TestCase):
    if not getattr(unittest.TestCase, "assertRaisesRegex", False):
        assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


def make_cffi(cls):
    """Decorator to add CFFI versions of each test method."""

    # The module containing this class definition should
    # `import zstandard as zstd`. Otherwise things may blow up.
    mod = inspect.getmodule(cls)
    if not hasattr(mod, "zstd"):
        raise Exception('test module does not contain "zstd" symbol')

    if not hasattr(mod.zstd, "backend"):
        raise Exception(
            'zstd symbol does not have "backend" attribute; did '
            "you `import zstandard as zstd`?"
        )

    # If `import zstandard` already chose the cffi backend, there is nothing
    # for us to do: we only add the cffi variation if the default backend
    # is the C extension.
    if mod.zstd.backend == "cffi":
        return cls

    old_env = dict(os.environ)
    os.environ["PYTHON_ZSTANDARD_IMPORT_POLICY"] = "cffi"
    try:
        try:
            mod_info = imp.find_module("zstandard")
            mod = imp.load_module("zstandard_cffi", *mod_info)
        except ImportError:
            return cls
    finally:
        os.environ.clear()
        os.environ.update(old_env)

    if mod.backend != "cffi":
        raise Exception(
            "got the zstandard %s backend instead of cffi" % mod.backend
        )

    # If CFFI version is available, dynamically construct test methods
    # that use it.

    for attr in dir(cls):
        fn = getattr(cls, attr)
        if not inspect.ismethod(fn) and not inspect.isfunction(fn):
            continue

        if not fn.__name__.startswith("test_"):
            continue

        name = "%s_cffi" % fn.__name__

        # Replace the "zstd" symbol with the CFFI module instance. Then copy
        # the function object and install it in a new attribute.
        if isinstance(fn, types.FunctionType):
            globs = dict(fn.__globals__)
            globs["zstd"] = mod
            new_fn = types.FunctionType(
                fn.__code__, globs, name, fn.__defaults__, fn.__closure__
            )
            new_method = new_fn
        else:
            globs = dict(fn.__func__.func_globals)
            globs["zstd"] = mod
            new_fn = types.FunctionType(
                fn.__func__.func_code,
                globs,
                name,
                fn.__func__.func_defaults,
                fn.__func__.func_closure,
            )
            new_method = types.UnboundMethodType(
                new_fn, fn.im_self, fn.im_class
            )

        setattr(cls, name, new_method)

    return cls


class NonClosingBytesIO(io.BytesIO):
    """BytesIO that saves the underlying buffer on close().

    This allows us to access written data after close().
    """

    def __init__(self, *args, **kwargs):
        super(NonClosingBytesIO, self).__init__(*args, **kwargs)
        self._saved_buffer = None

    def close(self):
        self._saved_buffer = self.getvalue()
        return super(NonClosingBytesIO, self).close()

    def getvalue(self):
        if self.closed:
            return self._saved_buffer
        else:
            return super(NonClosingBytesIO, self).getvalue()


class OpCountingBytesIO(NonClosingBytesIO):
    def __init__(self, *args, **kwargs):
        self._flush_count = 0
        self._read_count = 0
        self._write_count = 0
        return super(OpCountingBytesIO, self).__init__(*args, **kwargs)

    def flush(self):
        self._flush_count += 1
        return super(OpCountingBytesIO, self).flush()

    def read(self, *args):
        self._read_count += 1
        return super(OpCountingBytesIO, self).read(*args)

    def write(self, data):
        self._write_count += 1
        return super(OpCountingBytesIO, self).write(data)


_source_files = []


def random_input_data():
    """Obtain the raw content of source files.

    This is used for generating "random" data to feed into fuzzing, since it is
    faster than random content generation.
    """
    if _source_files:
        return _source_files

    for root, dirs, files in os.walk(os.path.dirname(__file__)):
        dirs[:] = list(sorted(dirs))
        for f in sorted(files):
            try:
                with open(os.path.join(root, f), "rb") as fh:
                    data = fh.read()
                    if data:
                        _source_files.append(data)
            except OSError:
                pass

    # Also add some actual random data.
    _source_files.append(os.urandom(100))
    _source_files.append(os.urandom(1000))
    _source_files.append(os.urandom(10000))
    _source_files.append(os.urandom(100000))
    _source_files.append(os.urandom(1000000))

    return _source_files


def generate_samples():
    inputs = [
        b"foo",
        b"bar",
        b"abcdef",
        b"sometext",
        b"baz",
    ]

    samples = []

    for i in range(128):
        samples.append(inputs[i % 5])
        samples.append(inputs[i % 5] * (i + 3))
        samples.append(inputs[-(i % 5)] * (i + 2))

    return samples


if hypothesis:
    default_settings = hypothesis.settings(deadline=10000)
    hypothesis.settings.register_profile("default", default_settings)

    ci_settings = hypothesis.settings(deadline=20000, max_examples=1000)
    hypothesis.settings.register_profile("ci", ci_settings)

    expensive_settings = hypothesis.settings(deadline=None, max_examples=10000)
    hypothesis.settings.register_profile("expensive", expensive_settings)

    hypothesis.settings.load_profile(
        os.environ.get("HYPOTHESIS_PROFILE", "default")
    )
