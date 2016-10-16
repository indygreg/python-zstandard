set -ex

if [ -n "${CONDA}" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/
else
    tox
fi
