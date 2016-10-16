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
void decompressor_module_init(PyObject* mod);
void decompressionwriter_module_init(PyObject* mod);
void decompressoriterator_module_init(PyObject* mod);

void zstd_module_init(PyObject* m) {
	PyObject* version;
	PyObject* zstdVersion;
	PyObject* frameHeader;

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
	decompressor_module_init(m);
	decompressionwriter_module_init(m);
	decompressoriterator_module_init(m);
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
