import os
import sys
import sysconfig

import pytest

try:
    import hypothesis  # type: ignore
except ImportError:
    hypothesis = None  # type: ignore


def pytest_configure(config):
    if (
        os.environ.get("PYTHON_ZSTANDARD_IMPORT_POLICY", "").strip() == "cffi"
        and sysconfig.get_config_var("Py_GIL_DISABLED") == 1
        and sys.version_info[0:2] == (3, 13)
    ):
        pytest.exit(
            "cffi backend not supported on 3.13 free-threaded Python", 0
        )


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
