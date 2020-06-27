================
python-zstandard
================

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

|  |ci-status|

.. |ci-status| image:: https://dev.azure.com/gregoryszorc/python-zstandard/_apis/build/status/indygreg.python-zstandard?branchName=master
    :target: https://dev.azure.com/gregoryszorc/python-zstandard/_apis/build/status/indygreg.python-zstandard?branchName=master
