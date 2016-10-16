/**
* Copyright (c) 2016-present, Gregory Szorc
* All rights reserved.
*
* This software may be modified and distributed under the terms
* of the BSD license. See the LICENSE file for details.
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define ZSTD_STATIC_LINKING_ONLY
#define ZDICT_STATIC_LINKING_ONLY
#include "mem.h"
#include "zstd.h"
#include "zdict.h"

typedef struct {
	PyObject_HEAD
	unsigned windowLog;
	unsigned chainLog;
	unsigned hashLog;
	unsigned searchLog;
	unsigned searchLength;
	unsigned targetLength;
	ZSTD_strategy strategy;
} CompressionParametersObject;

extern PyTypeObject CompressionParametersType;

typedef struct {
	PyObject_HEAD
	unsigned selectivityLevel;
	int compressionLevel;
	unsigned notificationLevel;
	unsigned dictID;
} DictParametersObject;

typedef struct {
	PyObject_HEAD

	void* dictData;
	size_t dictSize;
} ZstdCompressionDict;

typedef struct {
	PyObject_HEAD

	int compressionLevel;
	ZstdCompressionDict* dict;
	ZSTD_CDict* cdict;
	CompressionParametersObject* cparams;
	ZSTD_frameParameters fparams;
} ZstdCompressor;

typedef struct {
	PyObject_HEAD

	ZstdCompressor* compressor;
	ZSTD_CStream* cstream;
	ZSTD_outBuffer output;
	int flushed;
} ZstdCompressionObj;

typedef struct {
	PyObject_HEAD

	ZstdCompressor* compressor;
	PyObject* writer;
	Py_ssize_t sourceSize;
	size_t outSize;
	ZSTD_CStream* cstream;
	int entered;
} ZstdCompressionWriter;

typedef struct {
	PyObject_HEAD

	ZstdCompressor* compressor;
	PyObject* reader;
	Py_ssize_t sourceSize;
	size_t inSize;
	size_t outSize;

	ZSTD_CStream* cstream;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	int finishedOutput;
	int finishedInput;
	PyObject* readResult;
} ZstdCompressorIterator;

typedef struct {
	PyObject_HEAD

	ZstdCompressionDict* dict;
	ZSTD_DDict* ddict;
} ZstdDecompressor;

typedef struct {
	PyObject_HEAD

	ZstdDecompressor* decompressor;
	PyObject* writer;
	size_t outSize;
	ZSTD_DStream* dstream;
	int entered;
} ZstdDecompressionWriter;

typedef struct {
	PyObject_HEAD

	ZstdDecompressor* decompressor;
	PyObject* reader;
	size_t inSize;
	size_t outSize;
	ZSTD_DStream* dstream;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	Py_ssize_t readCount;
	int finishedInput;
	int finishedOutput;
} ZstdDecompressorIterator;

typedef struct {
	int errored;
	PyObject* chunk;
} DecompressorIteratorResult;
