#!/usr/bin/env bash
# Copyright (c) 2018-present, Gregory Szorc
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the BSD license. See the LICENSE file for details.

set -ex

MANYLINUX_PYPATHS="cp27-cp27m cp27-cp27mu cp34-cp34m cp35-cp35m cp36-cp36m"

function make_manylinux_wheels {
    image=$1
    pre_command=$2

    for path in ${MANYLINUX_PYPATHS}; do
        pypath=/opt/python/${path}

        docker run \
            -it \
            --rm \
            -e "PYPATH=${pypath}" \
            -v `pwd`:/project \
            -v `pwd`/dist:/output \
            ${image} \
            ${pre_command} /project/ci/build-manylinux-wheel.sh
    done
}

if [ "${BUILDMODE}" = "conda" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/

elif [ "${BUILDMODE}" = "manylinuxwheels" ]; then
    make_manylinux_wheels quay.io/pypa/manylinux1_x86_64
    make_manylinux_wheels quay.io/pypa/manylinux1_i686 linux32
elif [ "${BUILDMODE}" = "cibuildwheel" ]; then
    cibuildwheel --output-dir dist
elif [ "${BUILDMODE}" = "tox" ]; then
    tox
elif [ -n "${BUILDMODE}" ]; then
    echo "unknown BUILDMODE: ${BUILDMODE}"
    exit 1
else
    echo "BUILDMODE must be defined"
    exit 1
fi
