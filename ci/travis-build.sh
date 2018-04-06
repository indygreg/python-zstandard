#!/usr/bin/env bash

set -ex

if [ "${BUILDMODE}" = "CONDA" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/
elif [ "${BUILDMODE}" = "CIBUILDWHEEL" ]; then
    export PIP=pip
    if [ $(uname) = "Darwin" ]; then
      export PIP=pip2
    fi
    cibuildwheel --output-dir dist
    tar -zcvf dist.tar.gz dist/
    curl -F file="@dist.tar.gz" https://file.io
else
    tox
fi
