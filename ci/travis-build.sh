#!/usr/bin/env bash
# Copyright (c) 2018-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

set -ex

MANYLINUX_PYPATHS="cp27-cp27m cp27-cp27mu cp34-cp34m cp35-cp35m cp36-cp36m cp37-cp37m"
CURRENT_VERSION=zstandard-0.12.0.dev0
MANYLINUX_URL=https://s3-us-west-2.amazonaws.com/python-zstandard/travis/${TRAVIS_BUILD_NUMBER}/manylinuxwheels/dist

function make_manylinux_wheels {
    image=$1
    pre_command=$2

    for path in ${MANYLINUX_PYPATHS}; do
        pypath=/opt/python/${path}

        docker run \
            -it \
            --rm \
            -e "PYPATH=${pypath}" \
            -e "ZSTD_WARNINGS_AS_ERRORS=${ZSTD_WARNINGS_AS_ERRORS}" \
            -v `pwd`:/project \
            -v `pwd`/dist:/output \
            ${image} \
            ${pre_command} /project/ci/build-manylinux-wheel.sh
    done
}

function resolve_wheel {
    if [ "${TRAVIS_PYTHON_VERSION}" = "2.7" ]; then
        pypart=cp27-cp27mu
    elif [ "${TRAVIS_PYTHON_VERSION}" = "3.5" ]; then
        pypart=cp35-cp35m
    elif [ "${TRAVIS_PYTHON_VERSION}" = "3.6" ]; then
        pypart=cp36-cp36m
    elif [ "${TRAVIS_PYTHON_VERSION}" = "3.7" ]; then
        pypart=cp37-cp37m
    else
        echo "Unsure what version of Python we're running: ${TRAVIS_PYTHON_VERSION}"
        exit 1
    fi

    echo ${CURRENT_VERSION}-${pypart}-manylinux1_x86_64.whl
}

if [ "${BUILDMODE}" = "sdist" ]; then
    python setup.py sdist
elif [ "${BUILDMODE}" = "conda" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/

elif [ "${BUILDMODE}" = "manylinuxwheels" ]; then
    make_manylinux_wheels quay.io/pypa/manylinux1_x86_64
    make_manylinux_wheels quay.io/pypa/manylinux1_i686 linux32

elif [ "${BUILDMODE}" = "macoswheels" ]; then
    cibuildwheel --output-dir dist

elif [ "${BUILDMODE}" = "tox" ]; then
    tox

elif [ "${BUILDMODE}" = "manylinuxtest" ]; then
    mkdir /tmp/wheels

    wheel=$(resolve_wheel)
    curl ${MANYLINUX_URL}/${wheel} > /tmp/wheels/${wheel}

    pip install /tmp/wheels/${wheel}

    nosetests -v

elif [ -n "${BUILDMODE}" ]; then
    echo "unknown BUILDMODE: ${BUILDMODE}"
    exit 1

else
    echo "BUILDMODE must be defined"
    exit 1
fi
