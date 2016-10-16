/**
 * Copyright (c) 2016-present, Gregory Szorc
 * All rights reserved.
 *
 * This software may be modified and distributed under the terms
 * of the BSD license. See the LICENSE file for details.
 */

/* A Python C extension for Zstandard. */

#include "python-zstandard.h"

#define PYTHON_ZSTANDARD_VERSION "0.4.0"

PyObject *ZstdError;

void ztopy_compression_parameters(CompressionParametersObject* params, ZSTD_compressionParameters* zparams) {
	zparams->windowLog = params->windowLog;
	zparams->chainLog = params->chainLog;
	zparams->hashLog = params->hashLog;
	zparams->searchLog = params->searchLog;
	zparams->searchLength = params->searchLength;
	zparams->targetLength = params->targetLength;
	zparams->strategy = params->strategy;
}

/**
* Initialize a zstd CStream from a ZstdCompressor instance.
*
* Returns a ZSTD_CStream on success or NULL on failure. If NULL, a Python
* exception will be set.
*/
ZSTD_CStream* CStream_from_ZstdCompressor(ZstdCompressor* compressor, Py_ssize_t sourceSize) {
	ZSTD_CStream* cstream;
	ZSTD_parameters zparams;
	void* dictData = NULL;
	size_t dictSize = 0;
	size_t zresult;

	cstream = ZSTD_createCStream();
	if (!cstream) {
		PyErr_SetString(ZstdError, "cannot create CStream");
		return NULL;
	}

	if (compressor->dict) {
		dictData = compressor->dict->dictData;
		dictSize = compressor->dict->dictSize;
	}

	memset(&zparams, 0, sizeof(zparams));
	if (compressor->cparams) {
		ztopy_compression_parameters(compressor->cparams, &zparams.cParams);
		/* Do NOT call ZSTD_adjustCParams() here because the compression params
		   come from the user. */
	}
	else {
		zparams.cParams = ZSTD_getCParams(compressor->compressionLevel, sourceSize, dictSize);
	}

	zparams.fParams = compressor->fparams;

	zresult = ZSTD_initCStream_advanced(cstream, dictData, dictSize, zparams, sourceSize);

	if (ZSTD_isError(zresult)) {
		ZSTD_freeCStream(cstream);
		PyErr_Format(ZstdError, "cannot init CStream: %s", ZSTD_getErrorName(zresult));
		return NULL;
	}

	return cstream;
}

static PyTypeObject ZstdDecompressionWriterType;

static PyTypeObject ZstdDecompressorIteratorType;

static ZSTD_DStream* DStream_from_ZstdDecompressor(ZstdDecompressor* decompressor) {
	ZSTD_DStream* dstream;
	void* dictData = NULL;
	size_t dictSize = 0;
	size_t zresult;

	dstream = ZSTD_createDStream();
	if (!dstream) {
		PyErr_SetString(ZstdError, "could not create DStream");
		return NULL;
	}

	if (decompressor->dict) {
		dictData = decompressor->dict->dictData;
		dictSize = decompressor->dict->dictSize;
	}

	if (dictData) {
		zresult = ZSTD_initDStream_usingDict(dstream, dictData, dictSize);
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

	ZstdCompressionDict* dict = NULL;

	self->dict = NULL;
	self->ddict = NULL;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|O!", kwlist,
		&ZstdCompressionDictType, &dict)) {
		return -1;
	}

	if (dict) {
		self->dict = dict;
		Py_INCREF(dict);
	}

	return 0;
}

static void ZstdDecompressor_dealloc(ZstdDecompressor* self) {
	Py_XDECREF(self->dict);

	if (self->ddict) {
		ZSTD_freeDDict(self->ddict);
		self->ddict = NULL;
	}

	PyObject_Del(self);
}

PyDoc_STRVAR(ZstdDecompressor_copy_stream__doc__,
"copy_stream(ifh, ofh[, read_size=default, write_size=default]) -- decompress data between streams\n"
"\n"
"Compressed data will be read from ``ifh``, decompressed, and written to\n"
"``ofh``. ``ifh`` must have a ``read(size)`` method. ``ofh`` must have a\n"
"``write(data)`` method.\n"
"\n"
"The optional ``read_size`` and ``write_size`` arguments control the chunk\n"
"size of data that is ``read()`` and ``write()`` between streams. They default\n"
"to the default input and output sizes of zstd decompressor streams.\n"
);

static PyObject* ZstdDecompressor_copy_stream(ZstdDecompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"ifh",
		"ofh",
		"read_size",
		"write_size",
		NULL
	};

	PyObject* source;
	PyObject* dest;
	size_t inSize = ZSTD_DStreamInSize();
	size_t outSize = ZSTD_DStreamOutSize();
	ZSTD_DStream* dstream;
	ZSTD_inBuffer input;
	ZSTD_outBuffer output;
	Py_ssize_t totalRead = 0;
	Py_ssize_t totalWrite = 0;
	char* readBuffer;
	Py_ssize_t readSize;
	PyObject* readResult;
	PyObject* res = NULL;
	size_t zresult = 0;
	PyObject* writeResult;
	PyObject* totalReadPy;
	PyObject* totalWritePy;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO|kk", kwlist, &source,
		&dest, &inSize, &outSize)) {
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

	output.dst = malloc(outSize);
	if (!output.dst) {
		PyErr_NoMemory();
		res = NULL;
		goto finally;
	}
	output.size = outSize;
	output.pos = 0;

	/* Read source stream until EOF */
	while (1) {
		readResult = PyObject_CallMethod(source, "read", "n", inSize);
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

		while (input.pos < input.size) {
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

				Py_XDECREF(writeResult);
				totalWrite += output.pos;
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
	if (output.dst) {
		free(output.dst);
	}

	if (dstream) {
		ZSTD_freeDStream(dstream);
	}

	return res;
}

PyDoc_STRVAR(ZstdDecompressor_decompress__doc__,
"decompress(data[, max_output_size=None]) -- Decompress data in its entirety\n"
"\n"
"This method will decompress the entirety of the argument and return the\n"
"result.\n"
"\n"
"The input bytes are expected to contain a full Zstandard frame (something\n"
"compressed with ``ZstdCompressor.compress()`` or similar). If the input does\n"
"not contain a full frame, an exception will be raised.\n"
"\n"
"If the frame header of the compressed data does not contain the content size\n"
"``max_output_size`` must be specified or ``ZstdError`` will be raised. An\n"
"allocation of size ``max_output_size`` will be performed and an attempt will\n"
"be made to perform decompression into that buffer. If the buffer is too\n"
"small or cannot be allocated, ``ZstdError`` will be raised. The buffer will\n"
"be resized if it is too large.\n"
"\n"
"Uncompressed data could be much larger than compressed data. As a result,\n"
"calling this function could result in a very large memory allocation being\n"
"performed to hold the uncompressed data. Therefore it is **highly**\n"
"recommended to use a streaming decompression method instead of this one.\n"
);

PyObject* ZstdDecompressor_decompress(ZstdDecompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"data",
		"max_output_size",
		NULL
	};

	const char* source;
	Py_ssize_t sourceSize;
	Py_ssize_t maxOutputSize = 0;
	unsigned long long decompressedSize;
	size_t destCapacity;
	PyObject* result = NULL;
	ZSTD_DCtx* dctx = NULL;
	void* dictData = NULL;
	size_t dictSize = 0;
	size_t zresult;

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y#|n", kwlist,
#else
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s#|n", kwlist,
#endif
		&source, &sourceSize, &maxOutputSize)) {
		return NULL;
	}

	dctx = ZSTD_createDCtx();
	if (!dctx) {
		PyErr_SetString(ZstdError, "could not create DCtx");
		return NULL;
	}

	if (self->dict) {
		dictData = self->dict->dictData;
		dictSize = self->dict->dictSize;
	}

	if (dictData && !self->ddict) {
		Py_BEGIN_ALLOW_THREADS
		self->ddict = ZSTD_createDDict(dictData, dictSize);
		Py_END_ALLOW_THREADS

		if (!self->ddict) {
			PyErr_SetString(ZstdError, "could not create decompression dict");
			goto except;
		}
	}

	decompressedSize = ZSTD_getDecompressedSize(source, sourceSize);
	/* 0 returned if content size not in the zstd frame header */
	if (0 == decompressedSize) {
		if (0 == maxOutputSize) {
			PyErr_SetString(ZstdError, "input data invalid or missing content size "
				"in frame header");
			goto except;
		}
		else {
			result = PyBytes_FromStringAndSize(NULL, maxOutputSize);
			destCapacity = maxOutputSize;
		}
	}
	else {
		result = PyBytes_FromStringAndSize(NULL, decompressedSize);
		destCapacity = decompressedSize;
	}

	if (!result) {
		goto except;
	}

	Py_BEGIN_ALLOW_THREADS
	if (self->ddict) {
		zresult = ZSTD_decompress_usingDDict(dctx, PyBytes_AsString(result), destCapacity,
			source, sourceSize, self->ddict);
	}
	else {
		zresult = ZSTD_decompress(PyBytes_AsString(result), destCapacity, source, sourceSize);
	}
	Py_END_ALLOW_THREADS

	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "decompression error: %s", ZSTD_getErrorName(zresult));
		goto except;
	}
	else if (decompressedSize && zresult != decompressedSize) {
		PyErr_Format(ZstdError, "decompression error: decompressed %d bytes; expected %d",
			zresult, decompressedSize);
		goto except;
	}
	else if (zresult < destCapacity) {
		if (_PyBytes_Resize(&result, zresult)) {
			goto except;
		}
	}

	goto finally;

except:
	Py_DecRef(result);
	result = NULL;

finally:
	if (dctx) {
		ZSTD_freeDCtx(dctx);
	}

	return result;
}

PyDoc_STRVAR(ZstdDecompressor_read_from__doc__,
"read_from(reader[, read_size=default, write_size=default])\n"
"Read compressed data and return an iterator\n"
"\n"
"Returns an iterator of decompressed data chunks produced from reading from\n"
"the ``reader``.\n"
"\n"
"Compressed data will be obtained from ``reader`` by calling the\n"
"``read(size)`` method of it. The source data will be streamed into a\n"
"decompressor. As decompressed data is available, it will be exposed to the\n"
"return iterator.\n"
"\n"
"Data is ``read()`` in chunks of size ``read_size`` and exposed to the\n"
"iterator in chunks of size ``write_size``. The default values are the input\n"
"and output sizes for a zstd streaming decompressor.\n"
);

static ZstdDecompressorIterator* ZstdDecompressor_read_from(ZstdDecompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"reader",
		"read_size",
		"write_size",
		NULL
	};

	PyObject* reader;
	size_t inSize = ZSTD_DStreamInSize();
	size_t outSize = ZSTD_DStreamOutSize();
	ZstdDecompressorIterator* result;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|kk", kwlist, &reader,
		&inSize, &outSize)) {
		return NULL;
	}

	if (!PyObject_HasAttrString(reader, "read")) {
		PyErr_SetString(PyExc_ValueError, "must pass an object with a read() method");
		return NULL;
	}

	result = PyObject_New(ZstdDecompressorIterator, &ZstdDecompressorIteratorType);
	if (!result) {
		return NULL;
	}

	result->decompressor = self;
	Py_INCREF(result->decompressor);

	result->reader = reader;
	Py_INCREF(result->reader);

	result->inSize = inSize;
	result->outSize = outSize;

	result->dstream = DStream_from_ZstdDecompressor(self);
	if (!result->dstream) {
		Py_DECREF(result);
		return NULL;
	}

	result->input.src = malloc(inSize);
	if (!result->input.src) {
		Py_DECREF(result);
		PyErr_NoMemory();
		return NULL;
	}
	result->input.size = 0;
	result->input.pos = 0;

	result->output.dst = NULL;
	result->output.size = 0;
	result->output.pos = 0;

	result->readCount = 0;
	result->finishedInput = 0;
	result->finishedOutput = 0;

	return result;
}

PyDoc_STRVAR(ZstdDecompressor_write_to__doc__,
"Create a context manager to write decompressed data to an object.\n"
"\n"
"The passed object must have a ``write()`` method.\n"
"\n"
"The caller feeds intput data to the object by calling ``write(data)``.\n"
"Decompressed data is written to the argument given as it is decompressed.\n"
"\n"
"An optional ``write_size`` argument defines the size of chunks to\n"
"``write()`` to the writer. It defaults to the default output size for a zstd\n"
"streaming decompressor.\n"
);

static ZstdDecompressionWriter* ZstdDecompressor_write_to(ZstdDecompressor* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"writer",
		"write_size",
		NULL
	};

	PyObject* writer;
	size_t outSize = ZSTD_DStreamOutSize();
	ZstdDecompressionWriter* result;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|k", kwlist, &writer, &outSize)) {
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

	result->outSize = outSize;

	result->entered = 0;
	result->dstream = NULL;

	return result;
}

static PyMethodDef ZstdDecompressor_methods[] = {
	{ "copy_stream", (PyCFunction)ZstdDecompressor_copy_stream, METH_VARARGS | METH_KEYWORDS,
	  ZstdDecompressor_copy_stream__doc__ },
	{ "decompress", (PyCFunction)ZstdDecompressor_decompress, METH_VARARGS | METH_KEYWORDS,
	  ZstdDecompressor_decompress__doc__ },
	{ "read_from", (PyCFunction)ZstdDecompressor_read_from, METH_VARARGS | METH_KEYWORDS,
	  ZstdDecompressor_read_from__doc__ },
	{ "write_to", (PyCFunction)ZstdDecompressor_write_to, METH_VARARGS | METH_KEYWORDS,
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

static PyObject* ZstdDecompressionWriter_memory_size(ZstdDecompressionWriter* self) {
	if (!self->dstream) {
		PyErr_SetString(ZstdError, "cannot determine size of inactive decompressor; "
			"call when context manager is active");
		return NULL;
	}

	return PyLong_FromSize_t(ZSTD_sizeof_DStream(self->dstream));
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

	output.dst = malloc(self->outSize);
	if (!output.dst) {
		return PyErr_NoMemory();
	}
	output.size = self->outSize;
	output.pos = 0;

	input.src = source;
	input.size = sourceSize;
	input.pos = 0;

	while ((ssize_t)input.pos < sourceSize) {
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
	{ "memory_size", (PyCFunction)ZstdDecompressionWriter_memory_size, METH_NOARGS,
	PyDoc_STR("Obtain the memory size in bytes of the underlying decompressor.") },
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

PyDoc_STRVAR(ZstdDecompressorIterator__doc__,
"Represents an iterator of decompressed data.\n"
);

static void ZstdDecompressorIterator_dealloc(ZstdDecompressorIterator* self) {
	Py_XDECREF(self->decompressor);
	Py_XDECREF(self->reader);

	if (self->dstream) {
		ZSTD_freeDStream(self->dstream);
		self->dstream = NULL;
	}

	if (self->input.src) {
		free((void*)self->input.src);
		self->input.src = NULL;
	}

	PyObject_Del(self);
}

static PyObject* ZstdDecompressorIterator_iter(PyObject* self) {
	Py_INCREF(self);
	return self;
}

static DecompressorIteratorResult read_decompressor_iterator(ZstdDecompressorIterator* self) {
	size_t zresult;
	PyObject* chunk;
	DecompressorIteratorResult result;
	size_t oldInputPos = self->input.pos;

	result.chunk = NULL;

	chunk = PyBytes_FromStringAndSize(NULL, self->outSize);
	if (!chunk) {
		result.errored = 1;
		return result;
	}

	self->output.dst = PyBytes_AsString(chunk);
	self->output.size = self->outSize;
	self->output.pos = 0;

	Py_BEGIN_ALLOW_THREADS
	zresult = ZSTD_decompressStream(self->dstream, &self->output, &self->input);
	Py_END_ALLOW_THREADS

	/* We're done with the pointer. Nullify to prevent anyone from getting a
	   handle on a Python object. */
	self->output.dst = NULL;

	if (ZSTD_isError(zresult)) {
		Py_DECREF(chunk);
		PyErr_Format(ZstdError, "zstd decompress error: %s",
			ZSTD_getErrorName(zresult));
		result.errored = 1;
		return result;
	}

	self->readCount += self->input.pos - oldInputPos;

	/* Frame is fully decoded. Input exhausted and output sitting in buffer. */
	if (0 == zresult) {
		self->finishedInput = 1;
		self->finishedOutput = 1;
	}

	/* If it produced output data, return it. */
	if (self->output.pos) {
		if (self->output.pos < self->outSize) {
			if (_PyBytes_Resize(&chunk, self->output.pos)) {
				result.errored = 1;
				return result;
			}
		}
	}
	else {
		Py_DECREF(chunk);
		chunk = NULL;
	}

	result.errored = 0;
	result.chunk = chunk;

	return result;
}

static PyObject* ZstdDecompressorIterator_iternext(ZstdDecompressorIterator* self) {
	PyObject* readResult;
	char* readBuffer;
	Py_ssize_t readSize;
	DecompressorIteratorResult result;

	if (self->finishedOutput) {
		PyErr_SetString(PyExc_StopIteration, "output flushed");
		return NULL;
	}

	/* If we have data left in the input, consume it. */
	if (self->input.pos < self->input.size) {
		result = read_decompressor_iterator(self);
		if (result.chunk || result.errored) {
			return result.chunk;
		}

		/* Else fall through to get more data from input. */
	}

read_from_source:

	if (!self->finishedInput) {
		readResult = PyObject_CallMethod(self->reader, "read", "I", self->inSize);
		if (!readResult) {
			return NULL;
		}

		PyBytes_AsStringAndSize(readResult, &readBuffer, &readSize);

		if (readSize) {
			/* Copy input into previously allocated buffer because it can live longer
			than a single function call and we don't want to keep a ref to a Python
			object around. This could be changed... */
			memcpy((void*)self->input.src, readBuffer, readSize);
			self->input.size = readSize;
			self->input.pos = 0;
		}
		/* No bytes on first read must mean an empty input stream. */
		else if (!self->readCount) {
			self->finishedInput = 1;
			self->finishedOutput = 1;
			Py_DECREF(readResult);
			PyErr_SetString(PyExc_StopIteration, "empty input");
			return NULL;
		}
		else {
			self->finishedInput = 1;
		}

		/* We've copied the data managed by memory. Discard the Python object. */
		Py_DECREF(readResult);
	}

	result = read_decompressor_iterator(self);
	if (result.errored || result.chunk) {
		return result.chunk;
	}

	/* No new output data. Try again unless we know there is no more data. */
	if (!self->finishedInput) {
		goto read_from_source;
	}

	PyErr_SetString(PyExc_StopIteration, "input exhausted");
	return NULL;
}

static PyTypeObject ZstdDecompressorIteratorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdDecompressorIterator",   /* tp_name */
	sizeof(ZstdDecompressorIterator),  /* tp_basicsize */
	0,                                 /* tp_itemsize */
	(destructor)ZstdDecompressorIterator_dealloc, /* tp_dealloc */
	0,                                 /* tp_print */
	0,                                 /* tp_getattr */
	0,                                 /* tp_setattr */
	0,                                 /* tp_compare */
	0,                                 /* tp_repr */
	0,                                 /* tp_as_number */
	0,                                 /* tp_as_sequence */
	0,                                 /* tp_as_mapping */
	0,                                 /* tp_hash */
	0,                                 /* tp_call */
	0,                                 /* tp_str */
	0,                                 /* tp_getattro */
	0,                                 /* tp_setattro */
	0,                                 /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdDecompressorIterator__doc__,   /* tp_doc */
	0,                                 /* tp_traverse */
	0,                                 /* tp_clear */
	0,                                 /* tp_richcompare */
	0,                                 /* tp_weaklistoffset */
	ZstdDecompressorIterator_iter,     /* tp_iter */
	(iternextfunc)ZstdDecompressorIterator_iternext, /* tp_iternext */
	0,                                 /* tp_methods */
	0,                                 /* tp_members */
	0,                                 /* tp_getset */
	0,                                 /* tp_base */
	0,                                 /* tp_dict */
	0,                                 /* tp_descr_get */
	0,                                 /* tp_descr_set */
	0,                                 /* tp_dictoffset */
	0,                                 /* tp_init */
	0,                                 /* tp_alloc */
	PyType_GenericNew,                /* tp_new */
};


PyDoc_STRVAR(estimate_compression_context_size__doc__,
"estimate_compression_context_size(compression_parameters)\n"
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

PyDoc_STRVAR(estimate_decompression_context_size__doc__,
"estimate_decompression_context_size()\n"
"\n"
"Estimate the amount of memory allocated to a decompression context.\n"
);

static PyObject* pyzstd_estimate_decompression_context_size(PyObject* self) {
	return PyLong_FromSize_t(ZSTD_estimateDCtxSize());
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

static ZstdCompressionDict* pyzstd_train_dictionary(PyObject* self, PyObject* args, PyObject* kwargs) {
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
	ZstdCompressionDict* result;

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
		PyErr_NoMemory();
		return NULL;
	}
	sampleSizes = malloc(samplesLen * sizeof(size_t));
	if (!sampleSizes) {
		free(sampleBuffer);
		PyErr_NoMemory();
		return NULL;
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
		PyErr_NoMemory();
		return NULL;
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

	result = PyObject_New(ZstdCompressionDict, &ZstdCompressionDictType);
	if (!result) {
		return NULL;
	}

	result->dictData = dict;
	result->dictSize = zresult;
	return result;
}

static char zstd_doc[] = "Interface to zstandard";

static PyMethodDef zstd_methods[] = {
	{ "estimate_compression_context_size", (PyCFunction)pyzstd_estimate_compression_context_size,
	METH_VARARGS, estimate_compression_context_size__doc__ },
	{ "estimate_decompression_context_size", (PyCFunction)pyzstd_estimate_decompression_context_size,
	METH_NOARGS, estimate_decompression_context_size__doc__ },
	{ "get_compression_parameters", (PyCFunction)pyzstd_get_compression_parameters,
	METH_VARARGS, get_compression_parameters__doc__ },
	{ "train_dictionary", (PyCFunction)pyzstd_train_dictionary,
	METH_VARARGS | METH_KEYWORDS, train_dictionary__doc__ },
	{ NULL, NULL }
};

static char frame_header[] = {
	'\x28',
	'\xb5',
	'\x2f',
	'\xfd',
};

void compressobj_module_init(PyObject* mod);
void compressor_module_init(PyObject* mod);
void compressionparams_module_init(PyObject* mod);
void dictparams_module_init(PyObject* mod);
void compressiondict_module_init(PyObject* mod);
void compressionwriter_module_init(PyObject* mod);
void compressoriterator_module_init(PyObject* mod);

void zstd_module_init(PyObject* m) {
	PyObject* version;
	PyObject* zstdVersion;
	PyObject* frameHeader;

	Py_TYPE(&ZstdDecompressorType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressorType) < 0) {
		return;
	}

	Py_TYPE(&ZstdDecompressionWriterType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressionWriterType) < 0) {
		return;
	}

	Py_TYPE(&ZstdDecompressorIteratorType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressorIteratorType) < 0) {
		return;
	}

#if PY_MAJOR_VERSION >= 3
	version = PyUnicode_FromString(PYTHON_ZSTANDARD_VERSION);
#else
	version = PyString_FromString(PYTHON_ZSTANDARD_VERSION);
#endif
	Py_INCREF(version);
	PyModule_AddObject(m, "__version__", version);

	ZstdError = PyErr_NewException("zstd.ZstdError", NULL, NULL);
	PyModule_AddObject(m, "ZstdError", ZstdError);

	/* For now, the version is a simple tuple instead of a dedicated type. */
	zstdVersion = PyTuple_New(3);
	PyTuple_SetItem(zstdVersion, 0, PyLong_FromLong(ZSTD_VERSION_MAJOR));
	PyTuple_SetItem(zstdVersion, 1, PyLong_FromLong(ZSTD_VERSION_MINOR));
	PyTuple_SetItem(zstdVersion, 2, PyLong_FromLong(ZSTD_VERSION_RELEASE));
	Py_IncRef(zstdVersion);
	PyModule_AddObject(m, "ZSTD_VERSION", zstdVersion);

	Py_INCREF((PyObject*)&ZstdDecompressorType);
	PyModule_AddObject(m, "ZstdDecompressor", (PyObject*)&ZstdDecompressorType);

	frameHeader = PyBytes_FromStringAndSize(frame_header, sizeof(frame_header));
	if (frameHeader) {
		PyModule_AddObject(m, "FRAME_HEADER", frameHeader);
	}
	else {
		PyErr_Format(PyExc_ValueError, "could not create frame header object");
	}

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

	compressionparams_module_init(m);
	dictparams_module_init(m);
	compressiondict_module_init(m);
	compressobj_module_init(m);
	compressor_module_init(m);
	compressionwriter_module_init(m);
	compressoriterator_module_init(m);
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
