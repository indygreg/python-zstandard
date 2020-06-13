#!/usr/bin/env python

# Downloads Azure Pipelines artifacts to a destination directory.

import argparse
import io
import pathlib
import zipfile

import requests


URL = "https://dev.azure.com/gregoryszorc/python-zstandard/_apis/build/builds/{build}/artifacts?api-version=4.1"

FETCH_NAME_PREFIXES = (
    "LinuxAnaconda",
    "MacOSWheel",
    "ManyLinuxWheel",
    "SourceDistribution",
    "WindowsAnaconda",
    "Windowsx64",
    "Windowsx86",
)


def download_artifacts(build: str, dest: pathlib.Path):
    if not dest.exists():
        dest.mkdir(parents=True)

    session = requests.session()

    index = session.get(URL.format(build=build)).json()

    for entry in index["value"]:
        if not entry["name"].startswith(FETCH_NAME_PREFIXES):
            print("skipping %s" % entry["name"])
            continue

        print("downloading %s" % entry["resource"]["downloadUrl"])
        zipdata = io.BytesIO(
            session.get(entry["resource"]["downloadUrl"]).content
        )

        with zipfile.ZipFile(zipdata, "r") as zf:
            for name in zf.namelist():
                name_path = pathlib.Path(name)
                dest_path = dest / name_path.name
                print("writing %s" % dest_path)

                with dest_path.open("wb") as fh:
                    fh.write(zf.read(name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("build", help='which build to download. e.g. "42"')
    parser.add_argument("dest", help="destination directory")

    args = parser.parse_args()

    download_artifacts(args.build, pathlib.Path(args.dest))
