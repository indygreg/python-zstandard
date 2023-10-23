import os

try:
    import hypothesis  # type: ignore
except ImportError:
    hypothesis = None  # type: ignore


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
