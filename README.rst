================
python-zstandard
================

![.github/workflows/test.yml](https://github.com/indygreg/python-zstandard/workflows/.github/workflows/test.yml/badge.svg)
![.github/workflows/wheel.yml](https://github.com/indygreg/python-zstandard/workflows/.github/workflows/wheel.yml/badge.svg)
![.github/workflows/typing.yml](https://github.com/indygreg/python-zstandard/workflows/.github/workflows/typing.yml/badge.svg)
![.github/workflows/anaconda.yml](https://github.com/indygreg/python-zstandard/workflows/.github/workflows/anaconda.yml/badge.svg)

This project provides Python bindings for interfacing with the
`Zstandard <http://www.zstd.net>`_ compression library. A C extension
and CFFI interface are provided.

The primary goal of the project is to provide a rich interface to the
underlying C API through a Pythonic interface while not sacrificing
performance. This means exposing most of the features and flexibility
of the C API while not sacrificing usability or safety that Python provides.

The canonical home for this project is
https://github.com/indygreg/python-zstandard.

For usage documentation, see https://python-zstandard.readthedocs.org/.
