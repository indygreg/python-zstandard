/**
* Copyright (c) 2017-present, Gregory Szorc
* All rights reserved.
*
* This software may be modified and distributed under the terms
* of the BSD license. See the LICENSE file for details.
*/

#include "python-zstandard.h"

extern PyObject* ZstdError;

static void set_unsupported_operation(void) {
	PyObject* iomod;
	PyObject* exc;

	iomod = PyImport_ImportModule("io");
	if (NULL == iomod) {
		return;
	}

	exc = PyObject_GetAttrString(iomod, "UnsupportedOperation");
	if (NULL == exc) {
		Py_DECREF(iomod);
		return;
	}

	PyErr_SetNone(exc);
	Py_DECREF(exc);
	Py_DECREF(iomod);
}

static void reader_dealloc(ZstdDecompressionReader* self) {
	Py_XDECREF(self->decompressor);
	Py_XDECREF(self->reader);

	if (self->buffer.buf) {
		PyBuffer_Release(&self->buffer);
	}

	PyObject_Del(self);
}

static ZstdDecompressionReader* reader_enter(ZstdDecompressionReader* self) {
	if (self->entered) {
		PyErr_SetString(PyExc_ValueError, "cannot __enter__ multiple times");
		return NULL;
	}

	if (ensure_dctx(self->decompressor, 1)) {
		return NULL;
	}

	self->entered = 1;

	Py_INCREF(self);
	return self;
}

static PyObject* reader_exit(ZstdDecompressionReader* self, PyObject* args) {
	PyObject* exc_type;
	PyObject* exc_value;
	PyObject* exc_tb;

	if (!PyArg_ParseTuple(args, "OOO:__exit__", &exc_type, &exc_value, &exc_tb)) {
		return NULL;
	}

	self->entered = 0;
	self->closed = 1;

	/* Release resources. */
	Py_CLEAR(self->reader);
	if (self->buffer.buf) {
		PyBuffer_Release(&self->buffer);
		memset(&self->buffer, 0, sizeof(self->buffer));
	}

	Py_CLEAR(self->decompressor);

	Py_RETURN_FALSE;
}

static PyObject* reader_readable(PyObject* self) {
	Py_RETURN_TRUE;
}

static PyObject* reader_writable(PyObject* self) {
	Py_RETURN_FALSE;
}

static PyObject* reader_seekable(PyObject* self) {
	Py_RETURN_TRUE;
}

static PyObject* reader_close(ZstdDecompressionReader* self) {
	self->closed = 1;
	Py_RETURN_NONE;
}

static PyObject* reader_closed(ZstdDecompressionReader* self) {
	if (self->closed) {
		Py_RETURN_TRUE;
	}
	else {
		Py_RETURN_FALSE;
	}
}

static PyObject* reader_flush(PyObject* self) {
	Py_RETURN_NONE;
}

static PyObject* reader_isatty(PyObject* self) {
	Py_RETURN_FALSE;
}

static PyObject* reader_read(ZstdDecompressionReader* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"size",
		NULL
	};

	Py_ssize_t size = -1;
	PyObject* result = NULL;
	char* resultBuffer;
	Py_ssize_t resultSize;
	ZSTD_outBuffer output;
	size_t zresult;

	if (!self->entered) {
		PyErr_SetString(ZstdError, "read() must be called from an active context manager");
		return NULL;
	}

	if (self->closed) {
		PyErr_SetString(PyExc_ValueError, "stream is closed");
		return NULL;
	}

	if (self->finishedOutput) {
		return PyBytes_FromStringAndSize("", 0);
	}

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "n", kwlist, &size)) {
		return NULL;
	}

	if (size < 1) {
		PyErr_SetString(PyExc_ValueError, "cannot read negative or size 0 amounts");
		return NULL;
	}

	result = PyBytes_FromStringAndSize(NULL, size);
	if (NULL == result) {
		return NULL;
	}

	PyBytes_AsStringAndSize(result, &resultBuffer, &resultSize);

	output.dst = resultBuffer;
	output.size = resultSize;
	output.pos = 0;

readinput:

	/* Consume input data left over from last time. */
	if (self->input.pos < self->input.size) {
		Py_BEGIN_ALLOW_THREADS
		zresult = ZSTD_decompress_generic(self->decompressor->dctx,
			&output, &self->input);
		Py_END_ALLOW_THREADS

		/* Input exhausted. Clear our state tracking. */
		if (self->input.pos == self->input.size) {
			memset(&self->input, 0, sizeof(self->input));
			Py_CLEAR(self->readResult);

			if (self->buffer.buf) {
				self->finishedInput = 1;
			}
		}

		if (ZSTD_isError(zresult)) {
			PyErr_Format(ZstdError, "zstd decompress error: %s", ZSTD_getErrorName(zresult));
			return NULL;
		}
		else if (0 == zresult) {
			self->finishedOutput = 1;
		}

		/* We fulfilled the full read request. Emit it. */
		if (output.pos && output.pos == output.size) {
			self->bytesDecompressed += output.size;
			return result;
		}

		/*
		 * There is more room in the output. Fall through to try to collect
		 * more data so we can try to fill the output.
		 */
	}

	if (!self->finishedInput) {
		if (self->reader) {
			Py_buffer buffer;

			assert(self->readResult == NULL);
			self->readResult = PyObject_CallMethod(self->reader, "read",
				"k", self->readSize);
			if (NULL == self->readResult) {
				return NULL;
			}

			memset(&buffer, 0, sizeof(buffer));

			if (0 != PyObject_GetBuffer(self->readResult, &buffer, PyBUF_CONTIG_RO)) {
				return NULL;
			}

			/* EOF */
			if (0 == buffer.len) {
				self->finishedInput = 1;
				Py_CLEAR(self->readResult);
			}
			else {
				self->input.src = buffer.buf;
				self->input.size = buffer.len;
				self->input.pos = 0;
			}

			PyBuffer_Release(&buffer);
		}
		else {
			assert(self->buffer.buf);
			/*
			 * We should only get here once since above block will exhaust
			 * source buffer until finishedInput is set.
			 */
			assert(self->input.src == NULL);

			self->input.src = self->buffer.buf;
			self->input.size = self->buffer.len;
			self->input.pos = 0;
		}
	}

	if (self->input.size) {
		goto readinput;
	}

	/* EOF */
	self->bytesDecompressed += output.pos;

	if (safe_pybytes_resize(&result, output.pos)) {
		Py_XDECREF(result);
		return NULL;
	}

	return result;
}

static PyObject* reader_readall(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyObject* reader_readline(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyObject* reader_readlines(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyObject* reader_seek(ZstdDecompressionReader* self, PyObject* args) {
	Py_ssize_t pos;
	int whence = 0;
	unsigned long long readAmount = 0;
	size_t defaultOutSize = ZSTD_DStreamOutSize();

	if (!self->entered) {
		PyErr_SetString(ZstdError, "seek() must be called from an active context manager");
		return NULL;
	}

	if (self->closed) {
		PyErr_SetString(PyExc_ValueError, "stream is closed");
		return NULL;
	}

	if (!PyArg_ParseTuple(args, "n|i:seek", &pos, &whence)) {
		return NULL;
	}

	if (whence == SEEK_SET) {
		if (pos < 0) {
			PyErr_SetString(PyExc_ValueError,
				"cannot seek to negative position with SEEK_SET");
			return NULL;
		}

		if ((unsigned long long)pos < self->bytesDecompressed) {
			PyErr_SetString(PyExc_ValueError,
				"cannot seek zstd decompression stream backwards");
			return NULL;
		}

		readAmount = pos - self->bytesDecompressed;
	}
	else if (whence == SEEK_CUR) {
		if (pos < 0) {
			PyErr_SetString(PyExc_ValueError,
				"cannot seek zstd decompression stream backwards");
			return NULL;
		}

		readAmount = pos;
	}
	else if (whence == SEEK_END) {
		/* We /could/ support this with pos==0. But let's not do that until someone
		   needs it. */
		PyErr_SetString(PyExc_ValueError,
			"zstd decompression streams cannot be seeked with SEEK_END");
		return NULL;
	}

	/* It is a bit inefficient to do this via the Python API. But since there
	   is a bit of state tracking involved to read from this type, it is the
	   easiest to implement. */
	while (readAmount) {
		Py_ssize_t readSize;
		PyObject* readResult = PyObject_CallMethod((PyObject*)self, "read", "K",
			readAmount < defaultOutSize ? readAmount : defaultOutSize);

		if (!readResult) {
			return NULL;
		}

		readSize = PyBytes_GET_SIZE(readResult);

		/* Empty read means EOF. */
		if (!readSize) {
			break;
		}

		readAmount -= readSize;
	}

	return PyLong_FromUnsignedLongLong(self->bytesDecompressed);
}

static PyObject* reader_tell(ZstdDecompressionReader* self) {
	/* TODO should this raise OSError since stream isn't seekable? */
	return PyLong_FromUnsignedLongLong(self->bytesDecompressed);
}

static PyObject* reader_write(PyObject* self, PyObject* args) {
	set_unsupported_operation();
	return NULL;
}

static PyObject* reader_writelines(PyObject* self, PyObject* args) {
	set_unsupported_operation();
	return NULL;
}

static PyObject* reader_iter(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyObject* reader_iternext(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyMethodDef reader_methods[] = {
	{ "__enter__", (PyCFunction)reader_enter, METH_NOARGS,
	PyDoc_STR("Enter a compression context") },
	{ "__exit__", (PyCFunction)reader_exit, METH_VARARGS,
	PyDoc_STR("Exit a compression context") },
	{ "close", (PyCFunction)reader_close, METH_NOARGS,
	PyDoc_STR("Close the stream so it cannot perform any more operations") },
	{ "closed", (PyCFunction)reader_closed, METH_NOARGS,
	PyDoc_STR("Whether stream is closed") },
	{ "flush", (PyCFunction)reader_flush, METH_NOARGS, PyDoc_STR("no-ops") },
	{ "isatty", (PyCFunction)reader_isatty, METH_NOARGS, PyDoc_STR("Returns False") },
	{ "readable", (PyCFunction)reader_readable, METH_NOARGS,
	PyDoc_STR("Returns True") },
	{ "read", (PyCFunction)reader_read, METH_VARARGS | METH_KEYWORDS,
	PyDoc_STR("read compressed data") },
	{ "readall", (PyCFunction)reader_readall, METH_NOARGS, PyDoc_STR("Not implemented") },
	{ "readline", (PyCFunction)reader_readline, METH_NOARGS, PyDoc_STR("Not implemented") },
	{ "readlines", (PyCFunction)reader_readlines, METH_NOARGS, PyDoc_STR("Not implemented") },
	{ "seek", (PyCFunction)reader_seek, METH_VARARGS, PyDoc_STR("Seek the stream") },
	{ "seekable", (PyCFunction)reader_seekable, METH_NOARGS,
	PyDoc_STR("Returns True") },
	{ "tell", (PyCFunction)reader_tell, METH_NOARGS,
	PyDoc_STR("Returns current number of bytes compressed") },
	{ "writable", (PyCFunction)reader_writable, METH_NOARGS,
	PyDoc_STR("Returns False") },
	{ "write", (PyCFunction)reader_write, METH_VARARGS, PyDoc_STR("unsupported operation") },
	{ "writelines", (PyCFunction)reader_writelines, METH_VARARGS, PyDoc_STR("unsupported operation") },
	{ NULL, NULL }
};

PyTypeObject ZstdDecompressionReaderType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdDecompressionReader", /* tp_name */
	sizeof(ZstdDecompressionReader), /* tp_basicsize */
	0, /* tp_itemsize */
	(destructor)reader_dealloc, /* tp_dealloc */
	0, /* tp_print */
	0, /* tp_getattr */
	0, /* tp_setattr */
	0, /* tp_compare */
	0, /* tp_repr */
	0, /* tp_as_number */
	0, /* tp_as_sequence */
	0, /* tp_as_mapping */
	0, /* tp_hash */
	0, /* tp_call */
	0, /* tp_str */
	0, /* tp_getattro */
	0, /* tp_setattro */
	0, /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT, /* tp_flags */
	0, /* tp_doc */
	0, /* tp_traverse */
	0, /* tp_clear */
	0, /* tp_richcompare */
	0, /* tp_weaklistoffset */
	reader_iter, /* tp_iter */
	reader_iternext, /* tp_iternext */
	reader_methods, /* tp_methods */
	0, /* tp_members */
	0, /* tp_getset */
	0, /* tp_base */
	0, /* tp_dict */
	0, /* tp_descr_get */
	0, /* tp_descr_set */
	0, /* tp_dictoffset */
	0, /* tp_init */
	0, /* tp_alloc */
	PyType_GenericNew, /* tp_new */
};


void decompressionreader_module_init(PyObject* mod) {
	/* TODO make reader a sub-class of io.RawIOBase */

	Py_TYPE(&ZstdDecompressionReaderType) = &PyType_Type;
	if (PyType_Ready(&ZstdDecompressionReaderType) < 0) {
		return;
	}
}
