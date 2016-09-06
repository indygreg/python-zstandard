/**
 * Copyright (c) 2016-present, Gregory Szorc
 * All rights reserved.
 *
 * This software may be modified and distributed under the terms
 * of the BSD license. See the LICENSE file for details.
 */

/* A Python C extension for Zstandard. */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define ZSTD_STATIC_LINKING_ONLY
#define ZDICT_STATIC_LINKING_ONLY
#include "zstd/common/mem.h"
#include "zstd.h"
#include "zstd/dictBuilder/zdict.h"

PyDoc_STRVAR(CompressionParameters__doc__,
"CompressionParameters: low-level control over zstd compression");

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

static PyObject* CompressionParameters_new(PyTypeObject* subtype, PyObject* args, PyObject* kwargs) {
	CompressionParametersObject* self;
	unsigned windowLog;
	unsigned chainLog;
	unsigned hashLog;
	unsigned searchLog;
	unsigned searchLength;
	unsigned targetLength;
	unsigned strategy;

	if (!PyArg_ParseTuple(args, "IIIIIII", &windowLog, &chainLog, &hashLog, &searchLog,
		&searchLength, &targetLength, &strategy)) {
		return NULL;
	}

	if (windowLog < ZSTD_WINDOWLOG_MIN || windowLog > ZSTD_WINDOWLOG_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid window log value");
		return NULL;
	}

	if (chainLog < ZSTD_CHAINLOG_MIN || chainLog > ZSTD_CHAINLOG_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid chain log value");
		return NULL;
	}

	if (hashLog < ZSTD_HASHLOG_MIN || hashLog > ZSTD_HASHLOG_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid hash log value");
		return NULL;
	}

	if (searchLog < ZSTD_SEARCHLOG_MIN || searchLog > ZSTD_SEARCHLOG_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid search log value");
		return NULL;
	}

	if (searchLength < ZSTD_SEARCHLENGTH_MIN || searchLength > ZSTD_SEARCHLENGTH_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid search length value");
		return NULL;
	}

	if (targetLength < ZSTD_TARGETLENGTH_MIN || targetLength > ZSTD_TARGETLENGTH_MAX) {
		PyErr_SetString(PyExc_ValueError, "invalid target length value");
		return NULL;
	}

	if (strategy < ZSTD_fast || strategy > ZSTD_btopt) {
		PyErr_SetString(PyExc_ValueError, "invalid strategy value");
		return NULL;
	}

	self = (CompressionParametersObject*)subtype->tp_alloc(subtype, 1);
	if (!self) {
		return NULL;
	}

	self->windowLog = windowLog;
	self->chainLog = chainLog;
	self->hashLog = hashLog;
	self->searchLog = searchLog;
	self->searchLength = searchLength;
	self->targetLength = targetLength;
	self->strategy = strategy;

	return (PyObject*)self;
}

static void CompressionParameters_dealloc(PyObject* self) {
	PyObject_Del(self);
}

static Py_ssize_t CompressionParameters_length(PyObject* self) {
	return 7;
};

static PyObject* CompressionParameters_item(PyObject* o, Py_ssize_t i) {
	CompressionParametersObject* self = (CompressionParametersObject*)o;

	switch (i) {
	case 0:
		return PyLong_FromLong(self->windowLog);
	case 1:
		return PyLong_FromLong(self->chainLog);
	case 2:
		return PyLong_FromLong(self->hashLog);
	case 3:
		return PyLong_FromLong(self->searchLog);
	case 4:
		return PyLong_FromLong(self->searchLength);
	case 5:
		return PyLong_FromLong(self->targetLength);
	case 6:
		return PyLong_FromLong(self->strategy);
	default:
		PyErr_SetString(PyExc_IndexError, "index out of range");
		return NULL;
	}
}

static PySequenceMethods CompressionParameters_sq = {
	CompressionParameters_length, /* sq_length */
	0,							  /* sq_concat */
	0,                            /* sq_repeat */
	CompressionParameters_item,   /* sq_item */
	0,                            /* sq_ass_item */
	0,                            /* sq_contains */
	0,                            /* sq_inplace_concat */
	0                             /* sq_inplace_repeat */
};

PyTypeObject CompressionParametersType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"CompressionParameters", /* tp_name */
	sizeof(CompressionParametersObject), /* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)CompressionParameters_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	&CompressionParameters_sq, /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	0,                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	CompressionParameters__doc__, /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	0,                         /* tp_methods */
	0,                         /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	CompressionParameters_new, /* tp_new */
};

PyDoc_STRVAR(FrameParameters__doc__,
	"FrameParameters: low-level control over zstd framing");

typedef struct {
	PyObject_HEAD
	unsigned contentSizeFlag;
	unsigned checksumFlag;
	unsigned noDictIDFlag;
} FrameParametersObject;

static PyObject* FrameParameters_new(PyTypeObject* subtype, PyObject* args, PyObject* kwargs) {
	FrameParametersObject* self;
	unsigned contentSizeFlag;
	unsigned checksumFlag;
	unsigned noDictIDFlag;

	if (!PyArg_ParseTuple(args, "III", &contentSizeFlag, &checksumFlag, &noDictIDFlag)) {
		return NULL;
	}

	self = (FrameParametersObject*)subtype->tp_alloc(subtype, 1);
	if (!self) {
		return NULL;
	}

	self->contentSizeFlag = contentSizeFlag;
	self->checksumFlag = checksumFlag;
	self->noDictIDFlag = noDictIDFlag;

	return (PyObject*)self;
}

static void FrameParameters_dealloc(PyObject* self) {
	PyObject_Del(self);
}

static Py_ssize_t FrameParameters_length(PyObject* self) {
	return 3;
};

static PyObject* FrameParameters_item(PyObject* o, Py_ssize_t i) {
	FrameParametersObject* self = (FrameParametersObject*)o;

	switch (i) {
	case 0:
		return PyLong_FromLong(self->contentSizeFlag);
	case 1:
		return PyLong_FromLong(self->checksumFlag);
	case 2:
		return PyLong_FromLong(self->noDictIDFlag);
	default:
		PyErr_SetString(PyExc_IndexError, "index out of range");
		return NULL;
	}
}

static PySequenceMethods FrameParameters_sq = {
	FrameParameters_length, /* sq_length */
	0,					    /* sq_concat */
	0,                      /* sq_repeat */
	FrameParameters_item,   /* sq_item */
	0,                      /* sq_ass_item */
	0,                      /* sq_contains */
	0,                      /* sq_inplace_concat */
	0                       /* sq_inplace_repeat */
};

PyTypeObject FrameParametersType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"FrameParameters", /* tp_name */
	sizeof(FrameParametersObject), /* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)FrameParameters_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	&FrameParameters_sq,       /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	0,                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	FrameParameters__doc__,    /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	0,                         /* tp_methods */
	0,                         /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	FrameParameters_new,      /* tp_new */
};

PyDoc_STRVAR(DictParameters__doc__,
	"DictParameters: low-level control over dictionary generation");

typedef struct {
	PyObject_HEAD
	unsigned selectivityLevel;
	int compressionLevel;
	unsigned notificationLevel;
	unsigned dictID;
} DictParametersObject;

static PyObject* DictParameters_new(PyTypeObject* subtype, PyObject* args, PyObject* kwargs) {
	DictParametersObject* self;
	unsigned selectivityLevel;
	int compressionLevel;
	unsigned notificationLevel;
	unsigned dictID;

	if (!PyArg_ParseTuple(args, "IiII", &selectivityLevel, &compressionLevel,
		&notificationLevel, &dictID)) {
		return NULL;
	}

	self = (DictParametersObject*)subtype->tp_alloc(subtype, 1);
	if (!self) {
		return NULL;
	}

	self->selectivityLevel = selectivityLevel;
	self->compressionLevel = compressionLevel;
	self->notificationLevel = notificationLevel;
	self->dictID = dictID;

	return (PyObject*)self;
}

static void DictParameters_dealloc(PyObject* self) {
	PyObject_Del(self);
}

static Py_ssize_t DictParameters_length(PyObject* self) {
	return 4;
};

static PyObject* DictParameters_item(PyObject* o, Py_ssize_t i) {
	DictParametersObject* self = (DictParametersObject*)o;

	switch (i) {
	case 0:
		return PyLong_FromLong(self->selectivityLevel);
	case 1:
		return PyLong_FromLong(self->compressionLevel);
	case 2:
		return PyLong_FromLong(self->notificationLevel);
	case 3:
		return PyLong_FromLong(self->dictID);
	default:
		PyErr_SetString(PyExc_IndexError, "index out of range");
		return NULL;
	}
}

static PySequenceMethods DictParameters_sq = {
	DictParameters_length, /* sq_length */
	0,	                   /* sq_concat */
	0,                     /* sq_repeat */
	DictParameters_item,   /* sq_item */
	0,                     /* sq_ass_item */
	0,                     /* sq_contains */
	0,                     /* sq_inplace_concat */
	0                      /* sq_inplace_repeat */
};

PyTypeObject DictParametersType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"DictParameters", /* tp_name */
	sizeof(DictParametersObject), /* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)DictParameters_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	&DictParameters_sq,        /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	0,                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	DictParameters__doc__,     /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	0,                         /* tp_methods */
	0,                         /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	DictParameters_new,        /* tp_new */
};


static PyObject *ZstdError;

static inline void ztopy_compression_parameters(CompressionParametersObject* params, ZSTD_compressionParameters* zparams) {
	zparams->windowLog = params->windowLog;
	zparams->chainLog = params->chainLog;
	zparams->hashLog = params->hashLog;
	zparams->searchLog = params->searchLog;
	zparams->searchLength = params->searchLength;
	zparams->targetLength = params->targetLength;
	zparams->strategy = params->strategy;
}

typedef struct {
	PyObject_HEAD

	int compressionLevel;
	void* dictData;
	size_t dictSize;
	CompressionParametersObject* cparams;

	size_t insize;
	size_t outsize;
} ZstdCompressor;

struct ZstdCompressionWriter;

/**
* Initialize a zstd CStream from a ZstdCompressor instance.
*
* Returns a ZSTD_CStream on success or NULL on failure. If NULL, a Python
* exception will be set.
*/
static ZSTD_CStream* CStream_from_ZstdCompressor(ZstdCompressor* compressor) {
	ZSTD_CStream* cstream;
	ZSTD_parameters zparams;
	size_t zresult;

	cstream = ZSTD_createCStream();
	if (!cstream) {
		PyErr_SetString(ZstdError, "cannot create CStream");
		return NULL;
	}

	if (compressor->cparams) {
		memset(&zparams, 0, sizeof(zparams));
		ztopy_compression_parameters(compressor->cparams, &zparams.cParams);
		zresult = ZSTD_initCStream_advanced(cstream,
			compressor->dictData, compressor->dictSize, zparams, 0);
	}
	else if (compressor->dictData) {
		zresult = ZSTD_initCStream_usingDict(cstream,
			compressor->dictData, compressor->dictSize, compressor->compressionLevel);
	}
	else {
		zresult = ZSTD_initCStream(cstream, compressor->compressionLevel);
	}

	if (ZSTD_isError(zresult)) {
		ZSTD_freeCStream(cstream);
		PyErr_Format(ZstdError, "cannot init CStream: %s", ZSTD_getErrorName(zresult));
		return NULL;
	}

	return cstream;
}

typedef struct {
	PyObject_HEAD

	ZstdCompressor* compressor;
	PyObject* writer;
	ZSTD_CStream* cstream;
	int entered;
} ZstdCompressionWriter;

static PyTypeObject ZstdCompressionWriterType;

PyDoc_STRVAR(ZstdCompressor__doc__,
"ZstdCompressor(level=None, dict_data=None, compression_params=None)\n"
"\n"
"Create an object used to perform Zstandard compression.\n"
"\n"
"An instance can compress data various ways. Instances can be used multiple\n"
"times. Each compression operation will use the compression parameters\n"
"defined at construction time.\n"
"\n"
"Compression can be configured via the following names arguments:\n"
"\n"
"level\n"
"   Integer compression level.\n"
"dict_data\n"
"   Binary data holding a computed compression dictionary.\n"
"compression_params\n"
"   A ``CompressionParameters`` instance defining low-level compression"
"   parameters. If defined, this will overwrite the ``level`` argument.\n"
);

static int ZstdCompressor_init(ZstdCompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"level",
		"dict_data",
		"compression_params",
		NULL
	};

	int level = 3;
	const char* dictData;
	Py_ssize_t dictSize = 0;
	CompressionParametersObject* params = NULL;

	self->dictData = NULL;
	self->dictSize = 0;
	self->cparams = NULL;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|iy#O!", kwlist,
#else
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|is#O!", kwlist,
#endif
		&level, &dictData, &dictSize,
		&CompressionParametersType, &params)) {
		return -1;
	}

	if (level < 1) {
		PyErr_SetString(PyExc_ValueError, "level must be greater than 0");
		return -1;
	}

	if (level > ZSTD_maxCLevel()) {
		PyErr_Format(PyExc_ValueError, "level must be less than %d",
			ZSTD_maxCLevel() + 1);
		return -1;
	}

	self->insize = ZSTD_CStreamInSize();
	self->outsize = ZSTD_CStreamOutSize();
	self->compressionLevel = level;

	/* TODO consider reusing Python object's memory. */
	if (dictSize) {
		self->dictData = malloc(dictSize);
		if (!self->dictData) {
			PyErr_NoMemory();
			return -1;
		}
		memcpy(self->dictData, dictData, dictSize);
		self->dictSize = dictSize;
	}

	if (params) {
		self->cparams = params;
		Py_INCREF(params);
	}

	return 0;
}

static void ZstdCompressor_dealloc(ZstdCompressor* self) {
	Py_XDECREF(self->cparams);

	if (self->dictData) {
		free(self->dictData);
		self->dictData = NULL;
	}

	PyObject_Del(self);
}

PyDoc_STRVAR(ZstdCompressor_copy_stream__doc__,
"copy_stream(ifh, ofh) -- compress data between streams\n"
"\n"
"Data will be read from ``ifh``, compressed, and written to ``ofh``.\n"
"``ifh`` must have a ``read(size)`` method. ``ofh`` must have a ``write(data)``\n"
"method.\n"
);

static PyObject* ZstdCompressor_copy_stream(ZstdCompressor* self, PyObject* args) {
	PyObject* source;
	PyObject* dest;
	ZSTD_CStream* cstream;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	Py_ssize_t totalRead = 0;
	Py_ssize_t totalWrite = 0;
	PyObject* readSizeArg = NULL;
	char* readBuffer;
	Py_ssize_t readSize;
	PyObject* readResult;
	PyObject* res = NULL;
	size_t zresult;
	PyObject* writeResult;
	PyObject* totalReadPy;
	PyObject* totalWritePy;

	if (!PyArg_ParseTuple(args, "OO", &source, &dest)) {
		return NULL;
	}

	if (!PyObject_HasAttrString(source, "read")) {
		PyErr_SetString(PyExc_ValueError, "first argument must have a read() method");
		return NULL;
	}

	if (!PyObject_HasAttrString(dest, "write")) {
		PyErr_SetString(PyExc_ValueError, "second argument must have a write() method");
		return NULL;
	}

	cstream = CStream_from_ZstdCompressor(self);
	if (!cstream) {
		res = NULL;
		goto finally;
	}

	output.dst = malloc(self->outsize);
	if (!output.dst) {
		PyErr_NoMemory();
		res = NULL;
		goto finally;
	}
	output.size = self->outsize;
	output.pos = 0;

	readSizeArg = PyLong_FromSize_t(self->insize);

	while (1) {
		/* Try to read from source stream. */
		readResult = PyObject_CallMethod(source, "read", "I", readSizeArg);
		if (!readResult) {
			PyErr_SetString(ZstdError, "could not read() from source");
			goto finally;
		}

		PyBytes_AsStringAndSize(readResult, &readBuffer, &readSize);

		/* If no data was read, we're at EOF. */
		if (0 == readSize) {
			break;
		}

		totalRead += readSize;

		/* Send data to compressor */
		input.src = readBuffer;
		input.size = readSize;
		input.pos = 0;

		while (input.pos < input.size) {
			Py_BEGIN_ALLOW_THREADS
			zresult = ZSTD_compressStream(cstream, &output, &input);
			Py_END_ALLOW_THREADS

			if (ZSTD_isError(zresult)) {
				res = NULL;
				PyErr_Format(ZstdError, "zstd compress error: %s", ZSTD_getErrorName(zresult));
				goto finally;
			}

			if (output.pos) {
#if PY_MAJOR_VERSION >= 3
				writeResult = PyObject_CallMethod(dest, "write", "y#",
#else
				writeResult = PyObject_CallMethod(dest, "write", "s#",
#endif
					output.dst, output.pos);
				if (PyLong_Check(writeResult)) {
					totalWrite += PyLong_AsSsize_t(writeResult);
				}
				Py_XDECREF(writeResult);
				output.pos = 0;
			}
		}
	}

	/* We've finished reading. Now flush the compressor stream. */
	while (1) {
		zresult = ZSTD_endStream(cstream, &output);
		if (ZSTD_isError(zresult)) {
			PyErr_Format(ZstdError, "error ending compression stream: %s",
				ZSTD_getErrorName(zresult));
			res = NULL;
			goto finally;
		}

		if (output.pos) {
#if PY_MAJOR_VERSION >= 3
			writeResult = PyObject_CallMethod(dest, "write", "y#",
#else
			writeResult = PyObject_CallMethod(dest, "write", "s#",
#endif
				output.dst, output.pos);
			if (PyLong_Check(writeResult)) {
				totalWrite += PyLong_AsSsize_t(writeResult);
			}
			Py_XDECREF(writeResult);
			output.pos = 0;
		}

		if (!zresult) {
			break;
		}
	}

	ZSTD_freeCStream(cstream);
	cstream = NULL;

	totalReadPy = PyLong_FromSsize_t(totalRead);
	totalWritePy = PyLong_FromSsize_t(totalWrite);
	res = PyTuple_Pack(2, totalReadPy, totalWritePy);
	Py_DecRef(totalReadPy);
	Py_DecRef(totalWritePy);

finally:
	Py_XDECREF(readSizeArg);

	if (output.dst) {
		free(output.dst);
	}

	if (cstream) {
		ZSTD_freeCStream(cstream);
	}

	return res;
}

PyDoc_STRVAR(ZstdCompressor_compress__doc__,
"compress(data)\n"
"\n"
"Compress data in a single operation.\n"
"\n"
"This is the simplest mechanism to perform compression: simply pass in a\n"
"value and get a compressed value back. It is almost the most prone to abuse.\n"
"The input and output values must fit in memory, so passing in very large\n"
"values can result in excessive memory usage. For this reason, one of the\n"
"streaming based APIs is preferred for larger values.\n"
);

static PyObject* ZstdCompressor_compress(ZstdCompressor* self, PyObject* args) {
	const char* source;
	Py_ssize_t sourceSize;
	size_t destSize;
	ZSTD_CCtx* cctx;
	PyObject* output;
	char* dest;
	size_t zresult;
	ZSTD_compressionParameters cparams;
	ZSTD_parameters zparams;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTuple(args, "y#", &source, &sourceSize)) {
#else
	if (!PyArg_ParseTuple(args, "s#", &source, &sourceSize)) {
#endif
		return NULL;
	}

	destSize = ZSTD_compressBound(sourceSize);
	output = PyBytes_FromStringAndSize(NULL, destSize);
	if (!output) {
		return NULL;
	}

	dest = PyBytes_AsString(output);

	cctx = ZSTD_createCCtx();
	if (!cctx) {
		PyErr_SetString(ZstdError, "could not create CCtx");
		return NULL;
	}

	memset(&zparams, 0, sizeof(zparams));
	if (!self->cparams) {
		zparams.cParams = ZSTD_getCParams(self->compressionLevel, sourceSize, self->dictSize);
	}
	else {
		ztopy_compression_parameters(self->cparams, &cparams);
		zparams.cParams = cparams;
	}

	Py_BEGIN_ALLOW_THREADS
	zresult = ZSTD_compress_advanced(cctx, dest, destSize, source, sourceSize,
		self->dictData, self->dictSize, zparams);
	Py_END_ALLOW_THREADS

	ZSTD_freeCCtx(cctx);

	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "cannot compress: %s", ZSTD_getErrorName(zresult));
		Py_CLEAR(output);
		return NULL;
	}
	else {
		Py_SIZE(output) = zresult;
	}

	return output;
}

PyDoc_STRVAR(ZstdCompressor_write_to___doc__,
"Create a context manager to write compressed data to an object.\n"
"\n"
"The passed object must have a ``write()`` method.\n"
"\n"
"The caller feeds input data to the object by calling ``compress(data)``.\n"
"Compressed data is written to the argument given to this function.\n"
);

static ZstdCompressionWriter* ZstdCompressor_write_to(ZstdCompressor* self, PyObject* args) {
	PyObject* writer;
	ZstdCompressionWriter* result;

	if (!PyArg_ParseTuple(args, "O", &writer)) {
		return NULL;
	}

	if (!PyObject_HasAttrString(writer, "write")) {
		PyErr_SetString(PyExc_ValueError, "must pass an object with a write() method");
		return NULL;
	}

	result = PyObject_New(ZstdCompressionWriter, &ZstdCompressionWriterType);
	if (!result) {
		return NULL;
	}

	result->compressor = self;
	Py_INCREF(result->compressor);

	result->writer = writer;
	Py_INCREF(result->writer);

	result->entered = 0;
	result->cstream = NULL;

	return result;
}

static PyMethodDef ZstdCompressor_methods[] = {
	{ "compress", (PyCFunction)ZstdCompressor_compress, METH_VARARGS,
	ZstdCompressor_compress__doc__ },
	{ "copy_stream", (PyCFunction)ZstdCompressor_copy_stream, METH_VARARGS,
	ZstdCompressor_copy_stream__doc__ },
	{ "write_to", (PyCFunction)ZstdCompressor_write_to, METH_VARARGS,
	ZstdCompressor_write_to___doc__ },
	{ NULL, NULL }
};

static PyTypeObject ZstdCompressorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdCompressor",         /* tp_name */
	sizeof(ZstdCompressor),        /* tp_basicsize */
	0,                              /* tp_itemsize */
	(destructor)ZstdCompressor_dealloc, /* tp_dealloc */
	0,                              /* tp_print */
	0,                              /* tp_getattr */
	0,                              /* tp_setattr */
	0,                              /* tp_compare */
	0,                              /* tp_repr */
	0,                              /* tp_as_number */
	0,                              /* tp_as_sequence */
	0,                              /* tp_as_mapping */
	0,                              /* tp_hash */
	0,                              /* tp_call */
	0,                              /* tp_str */
	0,                              /* tp_getattro */
	0,                              /* tp_setattro */
	0,                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdCompressor__doc__,          /* tp_doc */
	0,                              /* tp_traverse */
	0,                              /* tp_clear */
	0,                              /* tp_richcompare */
	0,                              /* tp_weaklistoffset */
	0,                              /* tp_iter */
	0,                              /* tp_iternext */
	ZstdCompressor_methods,         /* tp_methods */
	0,                              /* tp_members */
	0,                              /* tp_getset */
	0,                              /* tp_base */
	0,                              /* tp_dict */
	0,                              /* tp_descr_get */
	0,                              /* tp_descr_set */
	0,                              /* tp_dictoffset */
	(initproc)ZstdCompressor_init,  /* tp_init */
	0,                              /* tp_alloc */
	PyType_GenericNew,              /* tp_new */
};

PyDoc_STRVAR(ZstdCompresssionWriter__doc__,
"""A context manager used for writing compressed output to a writer.\n"
);

static void ZstdCompressionWriter_dealloc(ZstdCompressionWriter* self) {
	Py_XDECREF(self->compressor);
	Py_XDECREF(self->writer);

	if (self->cstream) {
		ZSTD_freeCStream(self->cstream);
		self->cstream = NULL;
	}

	PyObject_Del(self);
}

static PyObject* ZstdCompressionWriter_enter(ZstdCompressionWriter* self) {
	if (self->entered) {
		PyErr_SetString(ZstdError, "cannot __enter__ multiple times");
		return NULL;
	}

	self->cstream = CStream_from_ZstdCompressor(self->compressor);
	if (!self->cstream) {
		return NULL;
	}

	self->entered = 1;

	Py_INCREF(self);
	return (PyObject*)self;
}

static PyObject* ZstdCompressionWriter_exit(ZstdCompressionWriter* self, PyObject* args) {
	PyObject* exc_type;
	PyObject* exc_value;
	PyObject* exc_tb;
	size_t zresult;

	ZSTD_outBuffer output;
	PyObject* res;

	if (!PyArg_ParseTuple(args, "OOO", &exc_type, &exc_value, &exc_tb)) {
		return NULL;
	}

	self->entered = 0;

	if (self->cstream && exc_type == Py_None && exc_value == Py_None &&
		exc_tb == Py_None) {

		output.dst = malloc(self->compressor->outsize);
		if (!output.dst) {
			return PyErr_NoMemory();
		}
		output.size = self->compressor->outsize;
		output.pos = 0;

		while (1) {
			zresult = ZSTD_endStream(self->cstream, &output);
			if (ZSTD_isError(zresult)) {
				PyErr_Format(ZstdError, "error ending compression stream: %s",
					ZSTD_getErrorName(zresult));
				free(output.dst);
				return NULL;
			}

			if (output.pos) {
#if PY_MAJOR_VERSION >= 3
				res = PyObject_CallMethod(self->writer, "write", "y#",
#else
				res = PyObject_CallMethod(self->writer, "write", "s#",
#endif
					output.dst, output.pos);
				Py_XDECREF(res);
			}

			if (!zresult) {
				break;
			}

			output.pos = 0;
		}

		free(output.dst);
		ZSTD_freeCStream(self->cstream);
		self->cstream = NULL;
	}

	Py_RETURN_FALSE;
}

static PyObject* ZstdCompressionWriter_write(ZstdCompressionWriter* self, PyObject* args) {
	const char* source;
	Py_ssize_t sourceSize;
	size_t zresult;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	PyObject* res;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTuple(args, "y#", &source, &sourceSize)) {
#else
	if (!PyArg_ParseTuple(args, "s#", &source, &sourceSize)) {
#endif
		return NULL;
	}

	if (!self->entered) {
		PyErr_SetString(ZstdError, "compress must be called from an active context manager");
		return NULL;
	}

	output.dst = malloc(self->compressor->outsize);
	if (!output.dst) {
		return PyErr_NoMemory();
	}
	output.size = self->compressor->outsize;
	output.pos = 0;

	input.src = source;
	input.size = sourceSize;
	input.pos = 0;

	while ((ssize_t)input.pos < sourceSize) {
		Py_BEGIN_ALLOW_THREADS
		zresult = ZSTD_compressStream(self->cstream, &output, &input);
		Py_END_ALLOW_THREADS

		if (ZSTD_isError(zresult)) {
			free(output.dst);
			PyErr_Format(ZstdError, "zstd compress error: %s", ZSTD_getErrorName(zresult));
			return NULL;
		}

		/* Copy data from output buffer to writer. */
		if (output.pos) {
#if PY_MAJOR_VERSION >= 3
			res = PyObject_CallMethod(self->writer, "write", "y#",
#else
			res = PyObject_CallMethod(self->writer, "write", "s#",
#endif
				output.dst, output.pos);
			Py_XDECREF(res);
		}
		output.pos = 0;
	}

	free(output.dst);

	/* TODO return bytes written */
	Py_RETURN_NONE;
}

static PyMethodDef ZstdCompressionWriter_methods[] = {
	{ "__enter__", (PyCFunction)ZstdCompressionWriter_enter, METH_NOARGS,
	PyDoc_STR("Enter a compression context.") },
	{ "__exit__", (PyCFunction)ZstdCompressionWriter_exit, METH_VARARGS,
	PyDoc_STR("Exit a compression context.") },
	{ "write", (PyCFunction)ZstdCompressionWriter_write, METH_VARARGS,
	PyDoc_STR("Compress data") },
	{ NULL, NULL }
};

static PyTypeObject ZstdCompressionWriterType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdCompressionWriter",  /* tp_name */
	sizeof(ZstdCompressionWriter),  /* tp_basicsize */
	0,                              /* tp_itemsize */
	(destructor)ZstdCompressionWriter_dealloc, /* tp_dealloc */
	0,                              /* tp_print */
	0,                              /* tp_getattr */
	0,                              /* tp_setattr */
	0,                              /* tp_compare */
	0,                              /* tp_repr */
	0,                              /* tp_as_number */
	0,                              /* tp_as_sequence */
	0,                              /* tp_as_mapping */
	0,                              /* tp_hash */
	0,                              /* tp_call */
	0,                              /* tp_str */
	0,                              /* tp_getattro */
	0,                              /* tp_setattro */
	0,                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdCompresssionWriter__doc__,  /* tp_doc */
	0,                              /* tp_traverse */
	0,                              /* tp_clear */
	0,                              /* tp_richcompare */
	0,                              /* tp_weaklistoffset */
	0,                              /* tp_iter */
	0,                              /* tp_iternext */
	ZstdCompressionWriter_methods,  /* tp_methods */
	0,                              /* tp_members */
	0,                              /* tp_getset */
	0,                              /* tp_base */
	0,                              /* tp_dict */
	0,                              /* tp_descr_get */
	0,                              /* tp_descr_set */
	0,                              /* tp_dictoffset */
	0,                              /* tp_init */
	0,                              /* tp_alloc */
	PyType_GenericNew,              /* tp_new */
};

typedef struct {
	PyObject_HEAD

	void* dictData;
	size_t dictSize;
	size_t insize;
	size_t outsize;
} ZstdDecompressor;

typedef struct {
	PyObject_HEAD

	ZstdDecompressor* decompressor;
	PyObject* writer;
	ZSTD_DStream* dstream;
	int entered;
} ZstdDecompressionWriter;

static PyTypeObject ZstdDecompressionWriterType;

static ZSTD_DStream* DStream_from_ZstdDecompressor(ZstdDecompressor* decompressor) {
	ZSTD_DStream* dstream;
	size_t zresult;

	dstream = ZSTD_createDStream();
	if (!dstream) {
		PyErr_SetString(ZstdError, "could not create DStream");
		return NULL;
	}

	if (decompressor->dictData) {
		zresult = ZSTD_initDStream_usingDict(dstream,
			decompressor->dictData, decompressor->dictSize);
	}
	else {
		zresult = ZSTD_initDStream(dstream);
	}

	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "could not initialize DStream: %s",
			ZSTD_getErrorName(zresult));
		return NULL;
	}

	return dstream;
}

PyDoc_STRVAR(ZstdDecompressor__doc__,
"ZstdDecompressor(dict_data=None)\n"
"\n"
"Create an object used to perform Zstandard decompression.\n"
"\n"
"An instance can perform multiple decompression operations."
);

static int ZstdDecompressor_init(ZstdDecompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"dict_data",
		NULL
	};

	const char* dictData;
	Py_ssize_t dictSize = 0;

	self->dictData = NULL;
	self->dictSize = 0;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|y#", kwlist,
#else
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|s#", kwlist,
#endif
		&dictData, &dictSize)) {
		return -1;
	}

	if (dictData) {
		self->dictData = malloc(dictSize);
		if (!self->dictData) {
			PyErr_NoMemory();
			return -1;
		}

		memcpy(self->dictData, dictData, dictSize);
		self->dictSize = dictSize;
	}

	self->insize = ZSTD_DStreamInSize();
	self->outsize = ZSTD_DStreamOutSize();

	return 0;
}

static void ZstdDecompressor_dealloc(ZstdDecompressor* self) {
	if (self->dictData) {
		free(self->dictData);
		self->dictData = NULL;
		self->dictSize = 0;
	}

	PyObject_Del(self);
}

PyDoc_STRVAR(ZstdDecompressor_copy_stream__doc__,
"copy_stream(ifh, ofh) -- decompress data between streams\n"
"\n"
"Compressed data will be read from ``ifh``, decompressed, and written to\n"
"``ofh``. ``ifh`` must have a ``read(size)`` method. ``ofh`` must have a\n"
"``write(data)`` method.\n"
);

static PyObject* ZstdDecompressor_copy_stream(ZstdDecompressor* self, PyObject* args) {
	PyObject* source;
	PyObject* dest;
	ZSTD_DStream* dstream;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	Py_ssize_t totalRead = 0;
	Py_ssize_t totalWrite = 0;
	PyObject* readSizeArg = NULL;
	char* readBuffer;
	Py_ssize_t readSize;
	PyObject* readResult;
	PyObject* res = NULL;
	size_t zresult = 0;
	PyObject* writeResult;
	PyObject* totalReadPy;
	PyObject* totalWritePy;

	if (!PyArg_ParseTuple(args, "OO", &source, &dest)) {
		return NULL;
	}

	if (!PyObject_HasAttrString(source, "read")) {
		PyErr_SetString(PyExc_ValueError, "first argument must have a read() method");
		return NULL;
	}

	if (!PyObject_HasAttrString(dest, "write")) {
		PyErr_SetString(PyExc_ValueError, "second argument must have a write() method");
		return NULL;
	}

	dstream = DStream_from_ZstdDecompressor(self);
	if (!dstream) {
		res = NULL;
		goto finally;
	}

	output.dst = malloc(self->outsize);
	if (!output.dst) {
		PyErr_NoMemory();
		res = NULL;
		goto finally;
	}
	output.size = self->outsize;
	output.pos = 0;

	readSizeArg = PyLong_FromSize_t(self->insize);

	/* Read source stream until EOF */
	while (1) {
		readResult = PyObject_CallMethod(source, "read", "I", readSizeArg);
		if (!readResult) {
			PyErr_SetString(ZstdError, "could not read() from source");
			goto finally;
		}

		PyBytes_AsStringAndSize(readResult, &readBuffer, &readSize);

		/* If no data was read, we're at EOF. */
		if (0 == readSize) {
			break;
		}

		totalRead += readSize;

		/* Send data to decompressor */
		input.src = readBuffer;
		input.size = readSize;
		input.pos = 0;

		while (input.pos < input.size || zresult == 1) {
			Py_BEGIN_ALLOW_THREADS
			zresult = ZSTD_decompressStream(dstream, &output, &input);
			Py_END_ALLOW_THREADS

			if (ZSTD_isError(zresult)) {
				PyErr_Format(ZstdError, "zstd decompressor error: %s",
					ZSTD_getErrorName(zresult));
				res = NULL;
				goto finally;
			}

			if (output.pos) {
#if PY_MAJOR_VERSION >= 3
				writeResult = PyObject_CallMethod(dest, "write", "y#",
#else
				writeResult = PyObject_CallMethod(dest, "write", "s#",
#endif
					output.dst, output.pos);

				if (PyLong_Check(writeResult)) {
					totalWrite += PyLong_AsSsize_t(writeResult);
				}
				Py_XDECREF(writeResult);
				output.pos = 0;
			}
		}
	}

	/* Source stream is exhausted. Finish up. */

	ZSTD_freeDStream(dstream);
	dstream = NULL;

	totalReadPy = PyLong_FromSsize_t(totalRead);
	totalWritePy = PyLong_FromSsize_t(totalWrite);
	res = PyTuple_Pack(2, totalReadPy, totalWritePy);
	Py_DecRef(totalReadPy);
	Py_DecRef(totalWritePy);

finally:
	Py_XDECREF(readSizeArg);

	if (output.dst) {
		free(output.dst);
	}

	if (dstream) {
		ZSTD_freeDStream(dstream);
	}

	return res;
}

PyDoc_STRVAR(ZstdDecompressor_write_to__doc__,
"Create a context manager to write decompressed data to an object.\n"
"\n"
"The passed object must have a ``write()`` method.\n"
"\n"
"The caller feeds intput data to the object by calling ``write(data)``.\n"
"Decompressed data is written to the argument given as it is decompressed.\n"
);

static ZstdDecompressionWriter* ZstdDecompressor_write_to(ZstdDecompressor* self, PyObject* args) {
	PyObject* writer;
	ZstdDecompressionWriter* result;

	if (!PyArg_ParseTuple(args, "O", &writer)) {
		return NULL;
	}

	if (!PyObject_HasAttrString(writer, "write")) {
		PyErr_SetString(PyExc_ValueError, "must pass an object with a write() method");
		return NULL;
	}

	result = PyObject_New(ZstdDecompressionWriter, &ZstdDecompressionWriterType);
	if (!result) {
		return NULL;
	}

	result->decompressor = self;
	Py_INCREF(result->decompressor);

	result->writer = writer;
	Py_INCREF(result->writer);

	result->entered = 0;
	result->dstream = NULL;

	return result;
}

static PyMethodDef ZstdDecompressor_methods[] = {
	{ "copy_stream", (PyCFunction)ZstdDecompressor_copy_stream, METH_VARARGS,
	  ZstdDecompressor_copy_stream__doc__ },
	{ "write_to", (PyCFunction)ZstdDecompressor_write_to, METH_VARARGS,
	  ZstdDecompressor_write_to__doc__ },
	{ NULL, NULL }
};

static PyTypeObject ZstdDecompressorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdDecompressor",        /* tp_name */
	sizeof(ZstdDecompressor),       /* tp_basicsize */
	0,                              /* tp_itemsize */
	(destructor)ZstdDecompressor_dealloc, /* tp_dealloc */
	0,                              /* tp_print */
	0,                              /* tp_getattr */
	0,                              /* tp_setattr */
	0,                              /* tp_compare */
	0,                              /* tp_repr */
	0,                              /* tp_as_number */
	0,                              /* tp_as_sequence */
	0,                              /* tp_as_mapping */
	0,                              /* tp_hash */
	0,                              /* tp_call */
	0,                              /* tp_str */
	0,                              /* tp_getattro */
	0,                              /* tp_setattro */
	0,                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdDecompressor__doc__,        /* tp_doc */
	0,                              /* tp_traverse */
	0,                              /* tp_clear */
	0,                              /* tp_richcompare */
	0,                              /* tp_weaklistoffset */
	0,                              /* tp_iter */
	0,                              /* tp_iternext */
	ZstdDecompressor_methods,       /* tp_methods */
	0,                              /* tp_members */
	0,                              /* tp_getset */
	0,                              /* tp_base */
	0,                              /* tp_dict */
	0,                              /* tp_descr_get */
	0,                              /* tp_descr_set */
	0,                              /* tp_dictoffset */
	(initproc)ZstdDecompressor_init,  /* tp_init */
	0,                              /* tp_alloc */
	PyType_GenericNew,              /* tp_new */
};

PyDoc_STRVAR(ZstdDecompressionWriter__doc,
"""A context manager used for writing decompressed output.\n"
);

static void ZstdDecompressionWriter_dealloc(ZstdDecompressionWriter* self) {
	Py_XDECREF(self->decompressor);
	Py_XDECREF(self->writer);

	if (self->dstream) {
		ZSTD_freeDStream(self->dstream);
		self->dstream = NULL;
	}

	PyObject_Del(self);
}

static PyObject* ZstdDecompressionWriter_enter(ZstdDecompressionWriter* self) {
	if (self->entered) {
		PyErr_SetString(ZstdError, "cannot __enter__ multiple times");
		return NULL;
	}

	self->dstream = DStream_from_ZstdDecompressor(self->decompressor);
	if (!self->dstream) {
		return NULL;
	}

	self->entered = 1;

	Py_INCREF(self);
	return (PyObject*)self;
}

static PyObject* ZstdDecompressionWriter_exit(ZstdDecompressionWriter* self, PyObject* args) {
	self->entered = 0;

	if (self->dstream) {
		ZSTD_freeDStream(self->dstream);
		self->dstream = NULL;
	}

	Py_RETURN_FALSE;
}

static PyObject* ZstdDecompressionWriter_write(ZstdDecompressionWriter* self, PyObject* args) {
	const char* source;
	Py_ssize_t sourceSize;
	size_t zresult = 0;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	PyObject* res;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTuple(args, "y#", &source, &sourceSize)) {
#else
	if (!PyArg_ParseTuple(args, "s#", &source, &sourceSize)) {
#endif
		return NULL;
	}

	if (!self->entered) {
		PyErr_SetString(ZstdError, "write must be called from an active context manager");
		return NULL;
	}

	output.dst = malloc(self->decompressor->outsize);
	if (!output.dst) {
		return PyErr_NoMemory();
	}
	output.size = self->decompressor->outsize;
	output.pos = 0;

	input.src = source;
	input.size = sourceSize;
	input.pos = 0;

	while ((ssize_t)input.pos < sourceSize || zresult == 1) {
		Py_BEGIN_ALLOW_THREADS
		zresult = ZSTD_decompressStream(self->dstream, &output, &input);
		Py_END_ALLOW_THREADS

		if (ZSTD_isError(zresult)) {
			free(output.dst);
			PyErr_Format(ZstdError, "zstd decompress error: %s",
				ZSTD_getErrorName(zresult));
			return NULL;
		}

		if (output.pos) {
#if PY_MAJOR_VERSION >= 3
			res = PyObject_CallMethod(self->writer, "write", "y#",
#else
			res = PyObject_CallMethod(self->writer, "write", "s#",
#endif
				output.dst, output.pos);
			Py_XDECREF(res);
			output.pos = 0;
		}
	}

	free(output.dst);

	/* TODO return bytes written */
	Py_RETURN_NONE;
}

static PyMethodDef ZstdDecompressionWriter_methods[] = {
	{ "__enter__", (PyCFunction)ZstdDecompressionWriter_enter, METH_NOARGS,
	PyDoc_STR("Enter a decompression context.") },
	{ "__exit__", (PyCFunction)ZstdDecompressionWriter_exit, METH_VARARGS,
	PyDoc_STR("Exit a decompression context.") },
	{ "write", (PyCFunction)ZstdDecompressionWriter_write, METH_VARARGS,
	PyDoc_STR("Compress data") },
	{ NULL, NULL }
};

static PyTypeObject ZstdDecompressionWriterType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdDecompressionWriter", /* tp_name */
	sizeof(ZstdDecompressionWriter),/* tp_basicsize */
	0,                              /* tp_itemsize */
	(destructor)ZstdDecompressionWriter_dealloc, /* tp_dealloc */
	0,                              /* tp_print */
	0,                              /* tp_getattr */
	0,                              /* tp_setattr */
	0,                              /* tp_compare */
	0,                              /* tp_repr */
	0,                              /* tp_as_number */
	0,                              /* tp_as_sequence */
	0,                              /* tp_as_mapping */
	0,                              /* tp_hash */
	0,                              /* tp_call */
	0,                              /* tp_str */
	0,                              /* tp_getattro */
	0,                              /* tp_setattro */
	0,                              /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdDecompressionWriter__doc,   /* tp_doc */
	0,                              /* tp_traverse */
	0,                              /* tp_clear */
	0,                              /* tp_richcompare */
	0,                              /* tp_weaklistoffset */
	0,                              /* tp_iter */
	0,                              /* tp_iternext */
	ZstdDecompressionWriter_methods,/* tp_methods */
	0,                              /* tp_members */
	0,                              /* tp_getset */
	0,                              /* tp_base */
	0,                              /* tp_dict */
	0,                              /* tp_descr_get */
	0,                              /* tp_descr_set */
	0,                              /* tp_dictoffset */
	0,                              /* tp_init */
	0,                              /* tp_alloc */
	PyType_GenericNew,              /* tp_new */
};

PyDoc_STRVAR(estimate_compress_context_size__doc__,
"estimate_compress_context_size(compression_parameters)\n"
"\n"
"Give the amount of memory allocated for a compression context given a\n"
"CompressionParameters instance");

static PyObject* pyzstd_estimate_compression_context_size(PyObject* self, PyObject* args) {
	CompressionParametersObject* params;
	ZSTD_compressionParameters zparams;
	PyObject* result;

	if (!PyArg_ParseTuple(args, "O!", &CompressionParametersType, &params)) {
		return NULL;
	}

	ztopy_compression_parameters(params, &zparams);
	result = PyLong_FromSize_t(ZSTD_estimateCCtxSize(zparams));
	return result;
}

PyDoc_STRVAR(get_compression_parameters__doc__,
"get_compression_parameters(compression_level[, source_size[, dict_size]])\n"
"\n"
"Obtains a ``CompressionParameters`` instance from a compression level and\n"
"optional input size and dictionary size");

static CompressionParametersObject* pyzstd_get_compression_parameters(PyObject* self, PyObject* args) {
	int compressionLevel;
	unsigned PY_LONG_LONG sourceSize = 0;
	Py_ssize_t dictSize = 0;
	ZSTD_compressionParameters params;
	CompressionParametersObject* result;

	if (!PyArg_ParseTuple(args, "i|Kn", &compressionLevel, &sourceSize, &dictSize)) {
		return NULL;
	}

	params = ZSTD_getCParams(compressionLevel, sourceSize, dictSize);

	result = PyObject_New(CompressionParametersObject, &CompressionParametersType);
	if (!result) {
		return NULL;
	}

	result->windowLog = params.windowLog;
	result->chainLog = params.chainLog;
	result->hashLog = params.hashLog;
	result->searchLog = params.searchLog;
	result->searchLength = params.searchLength;
	result->targetLength = params.targetLength;
	result->strategy = params.strategy;

	return result;
}

PyDoc_STRVAR(train_dictionary__doc__,
"train_dictionary(dict_size, samples)\n"
"\n"
"Train a dictionary from sample data.\n"
"\n"
"A compression dictionary of size ``dict_size`` will be created from the\n"
"iterable of samples provided by ``samples``.\n"
"\n"
"The raw dictionary content will be returned\n");

static PyObject* pyzstd_train_dictionary(PyObject* self, PyObject* args, PyObject* kwargs) {
	static char *kwlist[] = { "dict_size", "samples", "parameters", NULL };
	size_t capacity;
	PyObject* samples;
	Py_ssize_t samplesLen;
	PyObject* parameters = NULL;
	ZDICT_params_t zparams;
	Py_ssize_t sampleIndex;
	Py_ssize_t sampleSize;
	PyObject* sampleItem;
	size_t zresult;
	void* sampleBuffer;
	void* sampleOffset;
	size_t samplesSize = 0;
	size_t* sampleSizes;
	void* dict;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "nO!|O!", kwlist,
		&capacity,
		&PyList_Type, &samples,
		(PyObject*)&DictParametersType, &parameters)) {
		return NULL;
	}

	/* Validate parameters first since it is easiest. */
	zparams.selectivityLevel = 0;
	zparams.compressionLevel = 0;
	zparams.notificationLevel = 0;
	zparams.dictID = 0;
	zparams.reserved[0] = 0;
	zparams.reserved[1] = 0;

	if (parameters) {
		/* TODO validate data ranges */
		zparams.selectivityLevel = PyLong_AsUnsignedLong(PyTuple_GetItem(parameters, 0));
		zparams.compressionLevel = PyLong_AsLong(PyTuple_GetItem(parameters, 1));
		zparams.notificationLevel = PyLong_AsUnsignedLong(PyTuple_GetItem(parameters, 2));
		zparams.dictID = PyLong_AsUnsignedLong(PyTuple_GetItem(parameters, 3));
	}

	/* Figure out the size of the raw samples */
	samplesLen = PyList_Size(samples);
	for (sampleIndex = 0; sampleIndex < samplesLen; sampleIndex++) {
		sampleItem = PyList_GetItem(samples, sampleIndex);
		if (!PyBytes_Check(sampleItem)) {
			PyErr_SetString(PyExc_ValueError, "samples must be bytes");
			/* TODO probably need to perform DECREF here */
			return NULL;
		}
		samplesSize += PyBytes_GET_SIZE(sampleItem);
	}

	/* Now that we know the total size of the raw simples, we can allocate
	   a buffer for the raw data */
	sampleBuffer = malloc(samplesSize);
	if (!sampleBuffer) {
		return PyErr_NoMemory();
	}
	sampleSizes = malloc(samplesLen * sizeof(size_t));
	if (!sampleSizes) {
		free(sampleBuffer);
		return PyErr_NoMemory();
	}

	sampleOffset = sampleBuffer;
	/* Now iterate again and assemble the samples in the buffer */
	for (sampleIndex = 0; sampleIndex < samplesLen; sampleIndex++) {
		sampleItem = PyList_GetItem(samples, sampleIndex);
		sampleSize = PyBytes_GET_SIZE(sampleItem);
		sampleSizes[sampleIndex] = sampleSize;
		memcpy(sampleOffset, PyBytes_AS_STRING(sampleItem), sampleSize);
		sampleOffset = (char*)sampleOffset + sampleSize;
	}

	dict = malloc(capacity);
	if (!dict) {
		free(sampleSizes);
		free(sampleBuffer);
		return PyErr_NoMemory();
	}

	zresult = ZDICT_trainFromBuffer_advanced(dict, capacity,
		sampleBuffer, sampleSizes, (unsigned int)samplesLen,
		zparams);
	if (ZDICT_isError(zresult)) {
		PyErr_Format(ZstdError, "Cannot train dict: %s", ZDICT_getErrorName(zresult));
		free(dict);
		free(sampleSizes);
		free(sampleBuffer);
		return NULL;
	}

	/* TODO reference counting foo */
	return PyBytes_FromStringAndSize((char*)dict, zresult);
}

PyDoc_STRVAR(dictionary_id__doc__,
"dictionary_id(dict)\n"
"\n"
"Obtain the dictionary ID value for a compression dictionary.");

static PyObject* pyzstd_dictionary_id(PyObject* self, PyObject* args) {
	char* source;
	Py_ssize_t sourceSize;
	unsigned dictID;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTuple(args, "y#", &source, &sourceSize)) {
#else
	if (!PyArg_ParseTuple(args, "s#", &source, &sourceSize)) {
#endif
		PyErr_SetString(PyExc_ValueError, "must pass bytes data");
		return NULL;
	}

	dictID = ZDICT_getDictID((void*)source, sourceSize);
	return PyLong_FromLong(dictID);
}

static char zstd_doc[] = "Interface to zstandard";

static PyMethodDef zstd_methods[] = {
	{ "estimate_compression_context_size", (PyCFunction)pyzstd_estimate_compression_context_size,
	METH_VARARGS, estimate_compress_context_size__doc__ },
	{ "get_compression_parameters", (PyCFunction)pyzstd_get_compression_parameters,
	METH_VARARGS, get_compression_parameters__doc__ },
	{ "train_dictionary", (PyCFunction)pyzstd_train_dictionary,
	METH_VARARGS | METH_KEYWORDS, train_dictionary__doc__ },
	{ "dictionary_id", (PyCFunction)pyzstd_dictionary_id, METH_VARARGS,
	dictionary_id__doc__ },
	{ NULL, NULL }
};

void zstd_module_init(PyObject* m) {
	PyObject* version;

	Py_TYPE(&CompressionParametersType) = &PyType_Type;
	if (PyType_Ready(&CompressionParametersType) < 0) {
		return;
	}

	Py_TYPE(&FrameParametersType) = &PyType_Type;
	if (PyType_Ready(&FrameParametersType) < 0) {
		return;
	}

	Py_TYPE(&DictParametersType) = &PyType_Type;
	if (PyType_Ready(&DictParametersType) < 0) {
		return;
	}

	Py_TYPE(&ZstdCompressorType) = &PyType_Type;
	if (PyType_Ready(&ZstdCompressorType) < 0) {
		return;
	}

	Py_TYPE(&ZstdCompressionWriterType) = &PyType_Type;
	if (PyType_Ready(&ZstdCompressionWriterType) < 0) {
		return;
	}

	Py_TYPE(&ZstdDecompressorType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressorType) < 0) {
		return;
	}

	Py_TYPE(&ZstdDecompressionWriterType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressionWriterType) < 0) {
		return;
	}

	ZstdError = PyErr_NewException("zstd.ZstdError", NULL, NULL);

	/* For now, the version is a simple tuple instead of a dedicated type. */
	version = PyTuple_New(3);
	PyTuple_SetItem(version, 0, PyLong_FromLong(ZSTD_VERSION_MAJOR));
	PyTuple_SetItem(version, 1, PyLong_FromLong(ZSTD_VERSION_MINOR));
	PyTuple_SetItem(version, 2, PyLong_FromLong(ZSTD_VERSION_RELEASE));
	Py_IncRef(version);
	PyModule_AddObject(m, "ZSTD_VERSION", version);

	Py_IncRef((PyObject*)&CompressionParametersType);
	PyModule_AddObject(m, "CompressionParameters", (PyObject*)&CompressionParametersType);

	Py_IncRef((PyObject*)&FrameParametersType);
	PyModule_AddObject(m, "FrameParameters", (PyObject*)&FrameParametersType);

	Py_IncRef((PyObject*)&DictParametersType);
	PyModule_AddObject(m, "DictParameters", (PyObject*)&DictParametersType);

	Py_INCREF((PyObject*)&ZstdCompressorType);
	PyModule_AddObject(m, "ZstdCompressor", (PyObject*)&ZstdCompressorType);

	Py_INCREF((PyObject*)&ZstdDecompressorType);
	PyModule_AddObject(m, "ZstdDecompressor", (PyObject*)&ZstdDecompressorType);

	PyModule_AddIntConstant(m, "MAX_COMPRESSION_LEVEL", ZSTD_maxCLevel());
	PyModule_AddIntConstant(m, "COMPRESSION_RECOMMENDED_INPUT_SIZE",
		(long)ZSTD_CStreamInSize());
	PyModule_AddIntConstant(m, "COMPRESSION_RECOMMENDED_OUTPUT_SIZE",
		(long)ZSTD_CStreamOutSize());
	PyModule_AddIntConstant(m, "DECOMPRESSION_RECOMMENDED_INPUT_SIZE",
		(long)ZSTD_DStreamInSize());
	PyModule_AddIntConstant(m, "DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE",
		(long)ZSTD_DStreamOutSize());

	PyModule_AddIntConstant(m, "MAGIC_NUMBER", ZSTD_MAGICNUMBER);
	PyModule_AddIntConstant(m, "WINDOWLOG_MIN", ZSTD_WINDOWLOG_MIN);
	PyModule_AddIntConstant(m, "WINDOWLOG_MAX", ZSTD_WINDOWLOG_MAX);
	PyModule_AddIntConstant(m, "CHAINLOG_MIN", ZSTD_CHAINLOG_MIN);
	PyModule_AddIntConstant(m, "CHAINLOG_MAX", ZSTD_CHAINLOG_MAX);
	PyModule_AddIntConstant(m, "HASHLOG_MIN", ZSTD_HASHLOG_MIN);
	PyModule_AddIntConstant(m, "HASHLOG_MAX", ZSTD_HASHLOG_MAX);
	PyModule_AddIntConstant(m, "HASHLOG3_MAX", ZSTD_HASHLOG3_MAX);
	PyModule_AddIntConstant(m, "SEARCHLOG_MIN", ZSTD_SEARCHLOG_MIN);
	PyModule_AddIntConstant(m, "SEARCHLOG_MAX", ZSTD_SEARCHLOG_MAX);
	PyModule_AddIntConstant(m, "SEARCHLENGTH_MIN", ZSTD_SEARCHLENGTH_MIN);
	PyModule_AddIntConstant(m, "SEARCHLENGTH_MAX", ZSTD_SEARCHLENGTH_MAX);
	PyModule_AddIntConstant(m, "TARGETLENGTH_MIN", ZSTD_TARGETLENGTH_MIN);
	PyModule_AddIntConstant(m, "TARGETLENGTH_MAX", ZSTD_TARGETLENGTH_MAX);

	PyModule_AddIntConstant(m, "STRATEGY_FAST", ZSTD_fast);
	PyModule_AddIntConstant(m, "STRATEGY_DFAST", ZSTD_dfast);
	PyModule_AddIntConstant(m, "STRATEGY_GREEDY", ZSTD_greedy);
	PyModule_AddIntConstant(m, "STRATEGY_LAZY", ZSTD_lazy);
	PyModule_AddIntConstant(m, "STRATEGY_LAZY2", ZSTD_lazy2);
	PyModule_AddIntConstant(m, "STRATEGY_BTLAZY2", ZSTD_btlazy2);
	PyModule_AddIntConstant(m, "STRATEGY_BTOPT", ZSTD_btopt);
}

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef zstd_module = {
	PyModuleDef_HEAD_INIT,
	"zstd",
	zstd_doc,
	-1,
	zstd_methods
};

PyMODINIT_FUNC PyInit_zstd(void) {
	PyObject *m = PyModule_Create(&zstd_module);
	if (m) {
		zstd_module_init(m);
	}
	return m;
}
#else
PyMODINIT_FUNC initzstd(void) {
	PyObject *m = Py_InitModule3("zstd", zstd_methods, zstd_doc);
	if (m) {
		zstd_module_init(m);
	}
}
#endif

