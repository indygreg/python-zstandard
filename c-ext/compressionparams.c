/**
* Copyright (c) 2016-present, Gregory Szorc
* All rights reserved.
*
* This software may be modified and distributed under the terms
* of the BSD license. See the LICENSE file for details.
*/

#include "python-zstandard.h"

extern PyObject* ZstdError;

int set_parameter(ZSTD_CCtx_params* params, ZSTD_cParameter param, unsigned value) {
	size_t zresult = ZSTD_CCtxParam_setParameter(params, param, value);
	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "unable to set compression context parameter: %s",
			ZSTD_getErrorName(zresult));
		return 1;
	}

	return 0;
}

#define TRY_SET_PARAMETER(params, param, value) if (set_parameter(params, param, value)) return -1;

int set_parameters(ZSTD_CCtx_params* params, ZstdCompressionParametersObject* obj) {
	TRY_SET_PARAMETER(params, ZSTD_p_format, obj->format);
	TRY_SET_PARAMETER(params, ZSTD_p_compressionLevel, (unsigned)obj->compressionLevel);
	TRY_SET_PARAMETER(params, ZSTD_p_windowLog, obj->windowLog);
	TRY_SET_PARAMETER(params, ZSTD_p_hashLog, obj->hashLog);
	TRY_SET_PARAMETER(params, ZSTD_p_chainLog, obj->chainLog);
	TRY_SET_PARAMETER(params, ZSTD_p_searchLog, obj->searchLog);
	TRY_SET_PARAMETER(params, ZSTD_p_minMatch, obj->minMatch);
	TRY_SET_PARAMETER(params, ZSTD_p_targetLength, obj->targetLength);
	TRY_SET_PARAMETER(params, ZSTD_p_compressionStrategy, obj->compressionStrategy);
	TRY_SET_PARAMETER(params, ZSTD_p_contentSizeFlag, obj->contentSizeFlag);
	TRY_SET_PARAMETER(params, ZSTD_p_checksumFlag, obj->checksumFlag);
	TRY_SET_PARAMETER(params, ZSTD_p_dictIDFlag, obj->dictIDFlag);
	TRY_SET_PARAMETER(params, ZSTD_p_nbWorkers, obj->threads);
	TRY_SET_PARAMETER(params, ZSTD_p_jobSize, obj->jobSize);
	TRY_SET_PARAMETER(params, ZSTD_p_overlapSizeLog, obj->overlapSizeLog);
	TRY_SET_PARAMETER(params, ZSTD_p_compressLiterals, obj->compressLiterals);
	TRY_SET_PARAMETER(params, ZSTD_p_forceMaxWindow, obj->forceMaxWindow);
	TRY_SET_PARAMETER(params, ZSTD_p_enableLongDistanceMatching, obj->enableLongDistanceMatching);
	TRY_SET_PARAMETER(params, ZSTD_p_ldmHashLog, obj->ldmHashLog);
	TRY_SET_PARAMETER(params, ZSTD_p_ldmMinMatch, obj->ldmMinMatch);
	TRY_SET_PARAMETER(params, ZSTD_p_ldmBucketSizeLog, obj->ldmBucketSizeLog);
	TRY_SET_PARAMETER(params, ZSTD_p_ldmHashEveryLog, obj->ldmHashEveryLog);

	return 0;
}

int reset_params(ZstdCompressionParametersObject* params) {
	if (params->params) {
		ZSTD_CCtxParams_reset(params->params);
	}
	else {
		params->params = ZSTD_createCCtxParams();
		if (!params->params) {
			PyErr_NoMemory();
			return 1;
		}
	}

	return set_parameters(params->params, params);
}

static int ZstdCompressionParameters_init(ZstdCompressionParametersObject* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"format",
		"compression_level",
		"window_log",
		"hash_log",
		"chain_log",
		"search_log",
		"min_match",
		"target_length",
		"compression_strategy",
		"write_content_size",
		"write_checksum",
		"write_dict_id",
		"job_size",
		"overlap_size_log",
		"force_max_window",
		"enable_ldm",
		"ldm_hash_log",
		"ldm_min_match",
		"ldm_bucket_size_log",
		"ldm_hash_every_log",
		"threads",
		"compress_literals",
		NULL
	};

	unsigned format = 0;
	int compressionLevel = 0;
	unsigned windowLog = 0;
	unsigned hashLog = 0;
	unsigned chainLog = 0;
	unsigned searchLog = 0;
	unsigned minMatch = 0;
	unsigned targetLength = 0;
	unsigned compressionStrategy = 0;
	unsigned contentSizeFlag = 1;
	unsigned checksumFlag = 0;
	unsigned dictIDFlag = 0;
	unsigned jobSize = 0;
	unsigned overlapSizeLog = 0;
	unsigned forceMaxWindow = 0;
	unsigned enableLDM = 0;
	unsigned ldmHashLog = 0;
	unsigned ldmMinMatch = 0;
	unsigned ldmBucketSizeLog = 0;
	unsigned ldmHashEveryLog = 0;
	int threads = 0;

	/* Setting value 0 has the effect of disabling. So we use -1 as a default
	 * to detect whether to set. Then we automatically derive the expected value
	 * based on the level, just like zstandard does itself. */
	int compressLiterals = -1;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs,
		"|IiIIIIIIIIIIIIIIIIIIii:CompressionParameters",
		kwlist, &format, &compressionLevel, &windowLog, &hashLog, &chainLog,
		&searchLog, &minMatch, &targetLength, &compressionStrategy,
		&contentSizeFlag, &checksumFlag, &dictIDFlag, &jobSize, &overlapSizeLog,
		&forceMaxWindow, &enableLDM, &ldmHashLog, &ldmMinMatch, &ldmBucketSizeLog,
		&ldmHashEveryLog, &threads, &compressLiterals)) {
		return -1;
	}

	if (threads < 0) {
		threads = cpu_count();
	}

	if (compressLiterals < 0) {
		compressLiterals = compressionLevel >= 0;
	}

	self->format = format;
	self->compressionLevel = compressionLevel;
	self->windowLog = windowLog;
	self->hashLog = hashLog;
	self->chainLog = chainLog;
	self->searchLog = searchLog;
	self->minMatch = minMatch;
	self->targetLength = targetLength;
	self->compressionStrategy = compressionStrategy;
	self->contentSizeFlag = contentSizeFlag;
	self->checksumFlag = checksumFlag;
	self->dictIDFlag = dictIDFlag;
	self->threads = threads;
	self->jobSize = jobSize;
	self->overlapSizeLog = overlapSizeLog;
	self->compressLiterals = compressLiterals;
	self->forceMaxWindow = forceMaxWindow;
	self->enableLongDistanceMatching = enableLDM;
	self->ldmHashLog = ldmHashLog;
	self->ldmMinMatch = ldmMinMatch;
	self->ldmBucketSizeLog = ldmBucketSizeLog;
	self->ldmHashEveryLog = ldmHashEveryLog;

	if (reset_params(self)) {
		return -1;
	}

	return 0;
}

PyDoc_STRVAR(ZstdCompressionParameters_from_level__doc__,
"Create a CompressionParameters from a compression level and target sizes\n"
);

ZstdCompressionParametersObject* CompressionParameters_from_level(PyObject* undef, PyObject* args, PyObject* kwargs) {
	int managedKwargs = 0;
	int level;
	PyObject* sourceSize = NULL;
	PyObject* dictSize = NULL;
	unsigned PY_LONG_LONG iSourceSize = 0;
	Py_ssize_t iDictSize = 0;
	PyObject* val;
	ZSTD_compressionParameters params;
	ZstdCompressionParametersObject* result = NULL;
	int res;

	if (!PyArg_ParseTuple(args, "i:from_level",
		&level)) {
		return NULL;
	}

	if (!kwargs) {
		kwargs = PyDict_New();
		if (!kwargs) {
			return NULL;
		}
		managedKwargs = 1;
	}

	sourceSize = PyDict_GetItemString(kwargs, "source_size");
	if (sourceSize) {
#if PY_MAJOR_VERSION >= 3
		iSourceSize = PyLong_AsUnsignedLongLong(sourceSize);
		if (iSourceSize == (unsigned PY_LONG_LONG)(-1)) {
			goto cleanup;
		}
#else
		iSourceSize = PyInt_AsUnsignedLongLongMask(sourceSize);
#endif

		PyDict_DelItemString(kwargs, "source_size");
	}

	dictSize = PyDict_GetItemString(kwargs, "dict_size");
	if (dictSize) {
#if PY_MAJOR_VERSION >= 3
		iDictSize = PyLong_AsSsize_t(dictSize);
#else
		iDictSize = PyInt_AsSsize_t(dictSize);
#endif
		if (iDictSize == -1) {
			goto cleanup;
		}

		PyDict_DelItemString(kwargs, "dict_size");
	}


	params = ZSTD_getCParams(level, iSourceSize, iDictSize);

	/* Values derived from the input level and sizes are passed along to the
	   constructor. But only if a value doesn't already exist. */
	val = PyDict_GetItemString(kwargs, "window_log");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.windowLog);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "window_log", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "chain_log");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.chainLog);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "chain_log", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "hash_log");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.hashLog);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "hash_log", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "search_log");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.searchLog);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "search_log", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "min_match");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.searchLength);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "min_match", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "target_length");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.targetLength);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "target_length", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "compression_strategy");
	if (!val) {
		val = PyLong_FromUnsignedLong(params.strategy);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "compression_strategy", val);
		Py_DECREF(val);
	}

	val = PyDict_GetItemString(kwargs, "compress_literals");
	if (!val) {
		val = PyLong_FromLong(level >= 0 ? 1 : 0);
		if (!val) {
			goto cleanup;
		}
		PyDict_SetItemString(kwargs, "compress_literals", val);
		Py_DECREF(val);
	}

	result = PyObject_New(ZstdCompressionParametersObject, &ZstdCompressionParametersType);
	if (!result) {
		goto cleanup;
	}

	result->params = NULL;

	val = PyTuple_New(0);
	if (!val) {
		Py_CLEAR(result);
		goto cleanup;
	}

	res = ZstdCompressionParameters_init(result, val, kwargs);
	Py_DECREF(val);

	if (res) {
		Py_CLEAR(result);
		goto cleanup;
	}

cleanup:
	if (managedKwargs) {
		Py_DECREF(kwargs);
	}

	return result;
}

PyDoc_STRVAR(ZstdCompressionParameters_estimated_compression_context_size__doc__,
"Estimate the size in bytes of a compression context for compression parameters\n"
);

PyObject* ZstdCompressionParameters_estimated_compression_context_size(ZstdCompressionParametersObject* self) {
	return PyLong_FromSize_t(ZSTD_estimateCCtxSize_usingCCtxParams(self->params));
}

PyDoc_STRVAR(ZstdCompressionParameters__doc__,
"ZstdCompressionParameters: low-level control over zstd compression");

static void ZstdCompressionParameters_dealloc(ZstdCompressionParametersObject* self) {
	if (self->params) {
		ZSTD_freeCCtxParams(self->params);
		self->params = NULL;
	}

	PyObject_Del(self);
}

static PyMethodDef ZstdCompressionParameters_methods[] = {
	{
		"from_level",
		(PyCFunction)CompressionParameters_from_level,
		METH_VARARGS | METH_KEYWORDS | METH_STATIC,
		ZstdCompressionParameters_from_level__doc__
	},
	{
		"estimated_compression_context_size",
		(PyCFunction)ZstdCompressionParameters_estimated_compression_context_size,
		METH_NOARGS,
		ZstdCompressionParameters_estimated_compression_context_size__doc__
	},
	{ NULL, NULL }
};

static PyMemberDef ZstdCompressionParameters_members[] = {
	{ "format", T_UINT,
	  offsetof(ZstdCompressionParametersObject, format), READONLY,
	  "compression format" },
	{ "compression_level", T_INT,
	  offsetof(ZstdCompressionParametersObject, compressionLevel), READONLY,
	  "compression level" },
	{ "window_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, windowLog), READONLY,
	  "window log" },
	{ "hash_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, hashLog), READONLY,
	  "hash log" },
	{ "chain_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, chainLog), READONLY,
	  "chain log" },
	{ "search_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, searchLog), READONLY,
	  "search log" },
	{ "min_match", T_UINT,
	  offsetof(ZstdCompressionParametersObject, minMatch), READONLY,
	  "search length" },
	{ "target_length", T_UINT,
	  offsetof(ZstdCompressionParametersObject, targetLength), READONLY,
	  "target length" },
	{ "compression_strategy", T_UINT,
	  offsetof(ZstdCompressionParametersObject, compressionStrategy), READONLY,
	  "compression strategy" },
	{ "write_content_size", T_UINT,
	  offsetof(ZstdCompressionParametersObject, contentSizeFlag), READONLY,
	  "whether to write content size in frames" },
	{ "write_checksum", T_UINT,
	  offsetof(ZstdCompressionParametersObject, checksumFlag), READONLY,
	  "whether to write checksum in frames" },
	{ "write_dict_id", T_UINT,
	  offsetof(ZstdCompressionParametersObject, dictIDFlag), READONLY,
	  "whether to write dictionary ID in frames" },
	{ "threads", T_UINT,
	  offsetof(ZstdCompressionParametersObject, threads), READONLY,
	  "number of threads to use" },
	{ "job_size", T_UINT,
	  offsetof(ZstdCompressionParametersObject, jobSize), READONLY,
	  "size of compression job when using multiple threads" },
	{ "overlap_size_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, overlapSizeLog), READONLY,
	  "Size of previous input reloaded at the beginning of each job" },
	{ "compress_literals", T_UINT,
	  offsetof(ZstdCompressionParametersObject, compressLiterals), READONLY,
	  "whether Huffman compression of literals is in use" },
	{ "force_max_window", T_UINT,
	  offsetof(ZstdCompressionParametersObject, forceMaxWindow), READONLY,
	  "force back references to remain smaller than window size" },
	{ "enable_ldm", T_UINT,
	  offsetof(ZstdCompressionParametersObject, enableLongDistanceMatching), READONLY,
	  "whether to enable long distance matching" },
	{ "ldm_hash_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, ldmHashLog), READONLY,
	  "Size of the table for long distance matching, as a power of 2" },
	{ "ldm_min_match", T_UINT,
	  offsetof(ZstdCompressionParametersObject, ldmMinMatch), READONLY,
	  "minimum size of searched matches for long distance matcher" },
	{ "ldm_bucket_size_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, ldmBucketSizeLog), READONLY,
	  "log size of each bucket in the LDM hash table for collision resolution" },
	{ "ldm_hash_every_log", T_UINT,
	  offsetof(ZstdCompressionParametersObject, ldmHashEveryLog), READONLY,
	  "frequency of inserting/looking up entries in the LDM hash table" },
	{ NULL }
};

PyTypeObject ZstdCompressionParametersType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"ZstdCompressionParameters", /* tp_name */
	sizeof(ZstdCompressionParametersObject), /* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)ZstdCompressionParameters_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	0,                         /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	0,                         /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
	ZstdCompressionParameters__doc__, /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	ZstdCompressionParameters_methods, /* tp_methods */
	ZstdCompressionParameters_members, /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	(initproc)ZstdCompressionParameters_init, /* tp_init */
	0,                         /* tp_alloc */
	PyType_GenericNew,         /* tp_new */
};

void compressionparams_module_init(PyObject* mod) {
	Py_TYPE(&ZstdCompressionParametersType) = &PyType_Type;
	if (PyType_Ready(&ZstdCompressionParametersType) < 0) {
		return;
	}

	Py_INCREF(&ZstdCompressionParametersType);
	PyModule_AddObject(mod, "ZstdCompressionParameters",
		(PyObject*)&ZstdCompressionParametersType);

	/* TODO remove deprecated alias. */
	Py_INCREF(&ZstdCompressionParametersType);
	PyModule_AddObject(mod, "CompressionParameters",
		(PyObject*)&ZstdCompressionParametersType);
}
