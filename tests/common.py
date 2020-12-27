import io
import os

from typing import List

try:
    import hypothesis  # type: ignore
except ImportError:
    hypothesis = None  # type: ignore


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


class CustomBytesIO(io.BytesIO):
    def __init__(self, *args, **kwargs):
        self._flush_count = 0
        self._read_count = 0
        self._write_count = 0
        self.flush_exception = None
        self.read_exception = None
        self.write_exception = None
        super(CustomBytesIO, self).__init__(*args, **kwargs)

    def flush(self):
        self._flush_count += 1

        if self.flush_exception:
            raise self.flush_exception

        return super(CustomBytesIO, self).flush()

    def read(self, *args):
        self._read_count += 1

        if self.read_exception:
            raise self.read_exception

        return super(CustomBytesIO, self).read(*args)

    def write(self, data):
        self._write_count += 1

        if self.write_exception:
            raise self.write_exception

        return super(CustomBytesIO, self).write(data)


_source_files = []  # type: List[bytes]


def random_input_data():
    """Obtain the raw content of source files.

    This is used for generating "random" data to feed into fuzzing, since it is
    faster than random content generation.
    """
    if _source_files:
        return _source_files

    for root, dirs, files in os.walk(os.path.dirname(__file__)):
        # We filter out __pycache__ because there is a race between another
        # process writing cache files and us reading them.
        dirs[:] = list(sorted(d for d in dirs if d != "__pycache__"))
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


def get_optimal_dict_size_heuristically(src):
    return sum(len(ch) for ch in src) // 100


def generate_samples():
    inputs = [
        b"foo" * 32,
        b"bar" * 16,
        b"abcdef" * 64,
        b"sometext" * 128,
        b"baz" * 512,
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
