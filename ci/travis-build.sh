#!/usr/bin/env bash

set -ex

if [ "${BUILDMODE}" = "conda" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/
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
