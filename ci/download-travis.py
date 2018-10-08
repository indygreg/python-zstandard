#!/usr/bin/env python

# Downloads Travis artifacts to the local directory.
#
# This script is a bit hacky. But it gets the job done.

import argparse

import requests

BASE_URL = 'https://s3-us-west-2.amazonaws.com/python-zstandard/travis'

PATHS = [
    ('sdist', '.tar.gz'),
    ('manylinuxwheels', '-cp27-cp27m-manylinux1_i686.whl'),
    ('manylinuxwheels', '-cp27-cp27mu-manylinux1_i686.whl'),
    ('manylinuxwheels', '-cp34-cp34m-manylinux1_i686.whl'),
    ('manylinuxwheels', '-cp35-cp35m-manylinux1_i686.whl'),
    ('manylinuxwheels', '-cp36-cp36m-manylinux1_i686.whl'),
    ('manylinuxwheels', '-cp27-cp27m-manylinux1_x86_64.whl'),
    ('manylinuxwheels', '-cp27-cp27mu-manylinux1_x86_64.whl'),
    ('manylinuxwheels', '-cp34-cp34m-manylinux1_x86_64.whl'),
    ('manylinuxwheels', '-cp35-cp35m-manylinux1_x86_64.whl'),
    ('manylinuxwheels', '-cp36-cp36m-manylinux1_x86_64.whl'),
    ('manylinuxwheels', '-cp37-cp37m-manylinux1_x86_64.whl'),
    ('macos', '-cp27-cp27m-macosx_10_6_intel.whl'),
    ('macos', '-cp34-cp34m-macosx_10_6_intel.whl'),
    ('macos', '-cp35-cp35m-macosx_10_6_intel.whl'),
    ('macos', '-cp36-cp36m-macosx_10_6_intel.whl'),
    ('macos', '-cp37-cp37m-macosx_10_6_intel.whl'),
    ('conda/2.7', '-py27_0.tar.bz2'),
    ('conda/3.7', '-py37_0.tar.bz2'),
]

def make_request(session, url):
    return session.get(url)


def download_artifacts(build, version):
    session = requests.session()

    for path, suffix in PATHS:
        basename = 'zstandard-%s%s' % (version, suffix)
        url = '%s/%s/%s/dist/%s' % (BASE_URL, build, path, basename)

        response = make_request(session, url)

        if response.status_code != 200:
            print('non-200 from %s' % url)
            continue

        print('writing %s' % basename)
        with open(basename, 'wb') as fh:
            for chunk in response.iter_content(8192):
                fh.write(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('build', help='which build to download. e.g. "42"')
    parser.add_argument('version', help='python-zstandard version string')

    args = parser.parse_args()

    download_artifacts(args.build, args.version)
