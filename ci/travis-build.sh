#!/usr/bin/env bash

set -ex

if [ "${BUILDMODE}" = "CONDA" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/
elif [ "${BUILDMODE}" = "CIBUILDWHEEL" ]; then
    cibuildwheel --output-dir dist
else
    tox
fi
