#!/usr/bin/env python

"""Downloads GitHub Actions release artifacts."""

import argparse
import io
import pathlib
import zipfile

import requests

WORKFLOW_RUN_ARTIFACTS_URL = "https://api.github.com/repos/indygreg/python-zstandard/actions/runs/{run_id}/artifacts"


def download_artifacts(token: str, run_id: str, dest: pathlib.Path):
    if not dest.exists():
        dest.mkdir(parents=True)

    session = requests.session()
    session.headers["Authorization"] = "token %s" % token

    artifacts = session.get(
        WORKFLOW_RUN_ARTIFACTS_URL.format(run_id=run_id)
    ).json()

    for entry in artifacts["artifacts"]:
        download_url = entry["archive_download_url"]

        print("downloading %s" % download_url)
        zipdata = io.BytesIO(session.get(download_url).content)

        with zipfile.ZipFile(zipdata, "r") as zf:
            for name in zf.namelist():
                name_path = pathlib.Path(name)
                dest_path = dest / name_path.name
                print("writing %s" % dest_path)

                with dest_path.open("wb") as fh:
                    fh.write(zf.read(name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("token", help="GitHub token to authenticate with")
    parser.add_argument(
        "run_id", help='which GitHub Actions run download. e.g. "42"'
    )
    parser.add_argument("dest", help="destination directory")

    args = parser.parse_args()

    download_artifacts(args.token, args.run_id, pathlib.Path(args.dest))
