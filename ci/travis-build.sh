set -ex

if [ -n "${CONDA}" ]; then
    conda build ci/conda
    mkdir -p dist
    cp -av /home/travis/miniconda/conda-bld/*/*.tar.bz2 dist/
elif [ -n "${PIP}" ]; then
    cibuildwheel --output-dir dist
    tar -zcvf dist.tar.gz dist/
    curl -F file="@dist.tar.gz" https://file.io
else
    tox
fi
