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

static void reader_dealloc(ZstdCompressionReader* self) {
	Py_XDECREF(self->compressor);
	Py_XDECREF(self->reader);

	if (self->buffer.buf) {
		PyBuffer_Release(&self->buffer);
		memset(&self->buffer, 0, sizeof(self->buffer));
	}

	PyObject_Del(self);
}

static ZstdCompressionReader* reader_enter(ZstdCompressionReader* self) {
	size_t zresult;

	if (self->entered) {
		PyErr_SetString(PyExc_ValueError, "cannot __enter__ multiple times");
		return NULL;
	}

	zresult = ZSTD_CCtx_setPledgedSrcSize(self->compressor->cctx, self->sourceSize);
	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "error setting source size: %s",
			ZSTD_getErrorName(zresult));
		return NULL;
	}

	self->entered = 1;

	Py_INCREF(self);
	return self;
}

static PyObject* reader_exit(ZstdCompressionReader* self, PyObject* args) {
	PyObject* exc_type;
	PyObject* exc_value;
	PyObject* exc_tb;

	if (!PyArg_ParseTuple(args, "OOO:__exit__", &exc_type, &exc_value, &exc_tb)) {
		return NULL;
	}

	self->entered = 0;
	self->closed = 1;

	/* Release resources associated with source. */
	Py_CLEAR(self->reader);
	if (self->buffer.buf) {
		PyBuffer_Release(&self->buffer);
		memset(&self->buffer, 0, sizeof(self->buffer));
	}

    Py_CLEAR(self->compressor);

	Py_RETURN_FALSE;
}

static PyObject* reader_readable(ZstdCompressionReader* self) {
	Py_RETURN_TRUE;
}

static PyObject* reader_writable(ZstdCompressionReader* self) {
	Py_RETURN_FALSE;
}

static PyObject* reader_seekable(ZstdCompressionReader* self) {
	Py_RETURN_FALSE;
}

static PyObject* reader_readline(PyObject* self, PyObject* args) {
	set_unsupported_operation();
	return NULL;
}

static PyObject* reader_readlines(PyObject* self, PyObject* args) {
	set_unsupported_operation();
	return NULL;
}

static PyObject* reader_write(PyObject* self, PyObject* args) {
	PyErr_SetString(PyExc_OSError, "stream is not writable");
	return NULL;
}

static PyObject* reader_writelines(PyObject* self, PyObject* args) {
	PyErr_SetString(PyExc_OSError, "stream is not writable");
	return NULL;
}

static PyObject* reader_isatty(PyObject* self) {
	Py_RETURN_FALSE;
}

static PyObject* reader_flush(PyObject* self) {
	Py_RETURN_NONE;
}

static PyObject* reader_close(ZstdCompressionReader* self) {
	self->closed = 1;
	Py_RETURN_NONE;
}

static PyObject* reader_closed(ZstdCompressionReader* self) {
	if (self->closed) {
		Py_RETURN_TRUE;
	}
	else {
		Py_RETURN_FALSE;
	}
}

static PyObject* reader_tell(ZstdCompressionReader* self) {
	/* TODO should this raise OSError since stream isn't seekable? */
	return PyLong_FromUnsignedLongLong(self->bytesCompressed);
}

static PyObject* reader_read(ZstdCompressionReader* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"size",
		NULL
	};

	Py_ssize_t size = -1;
	PyObject* result = NULL;
	char* resultBuffer;
	Py_ssize_t resultSize;
	size_t zresult;
	size_t oldPos;

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

	self->output.dst = resultBuffer;
	self->output.size = resultSize;
	self->output.pos = 0;

readinput:

	/* If we have data left over, consume it. */
	if (self->input.pos < self->input.size) {
		oldPos = self->output.pos;

		Py_BEGIN_ALLOW_THREADS
		zresult = ZSTD_compress_generic(self->compressor->cctx,
			&self->output, &self->input, ZSTD_e_continue);

		Py_END_ALLOW_THREADS

		self->bytesCompressed += self->output.pos - oldPos;

		/* Input exhausted. Clear out state tracking. */
		if (self->input.pos == self->input.size) {
			memset(&self->input, 0, sizeof(self->input));
			Py_CLEAR(self->readResult);

			if (self->buffer.buf) {
				self->finishedInput = 1;
			}
		}

		if (ZSTD_isError(zresult)) {
			PyErr_Format(ZstdError, "zstd compress error: %s", ZSTD_getErrorName(zresult));
			return NULL;
		}

		if (self->output.pos) {
			/* If no more room in output, emit it. */
			if (self->output.pos == self->output.size) {
				memset(&self->output, 0, sizeof(self->output));
				return result;
			}

			/*
			 * There is room in the output. We fall through to below, which will either
			 * get more input for us or will attempt to end the stream.
			 */
		}

		/* Fall through to gather more input. */
	}

	if (!self->finishedInput) {
		if (self->reader) {
			Py_buffer buffer;

			assert(self->readResult == NULL);
			self->readResult = PyObject_CallMethod(self->reader, "read",
				"k", self->readSize);
			if (self->readResult == NULL) {
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

			self->input.src = self->buffer.buf;
			self->input.size = self->buffer.len;
			self->input.pos = 0;
		}
	}

	if (self->input.size) {
		goto readinput;
	}

	/* Else EOF */
	oldPos = self->output.pos;

	zresult = ZSTD_compress_generic(self->compressor->cctx, &self->output,
		&self->input, ZSTD_e_end);

	self->bytesCompressed += self->output.pos - oldPos;

	if (ZSTD_isError(zresult)) {
		PyErr_Format(ZstdError, "error ending compression stream: %s",
			ZSTD_getErrorName(zresult));
		return NULL;
	}

	assert(self->output.pos);

	if (0 == zresult) {
		self->finishedOutput = 1;
	}

	if (safe_pybytes_resize(&result, self->output.pos)) {
		Py_XDECREF(result);
		return NULL;
	}

	memset(&self->output, 0, sizeof(self->output));

	return result;
}

static PyObject* reader_readall(PyObject* self) {
	PyErr_SetNone(PyExc_NotImplementedError);
	return NULL;
}

static PyObject* reader_iter(PyObject* self) {
	set_unsupported_operation();
	return NULL;
}

static PyObject* reader_iternext(PyObject* self) {
	set_unsupported_operation();
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
	{ "read", (PyCFunction)reader_read, METH_VARARGS | METH_KEYWORDS, PyDoc_STR("read compressed data") },
	{ "readall", (PyCFunction)reader_readall, METH_NOARGS, PyDoc_STR("Not implemented") },
	{ "readline", (PyCFunction)reader_readline, METH_VARARGS, PyDoc_STR("Not implemented") },
	{ "readlines", (PyCFunction)reader_readlines, METH_VARARGS, PyDoc_STR("Not implemented") },
	{ "seekable", (PyCFunction)reader_seekable, METH_NOARGS,
	PyDoc_STR("Returns False") },
	{ "tell", (PyCFunction)reader_tell, METH_NOARGS,
	PyDoc_STR("Returns current number of bytes compressed") },
	{ "writable", (PyCFunction)reader_writable, METH_NOARGS,
	PyDoc_STR("Returns False") },
	{ "write", reader_write, METH_VARARGS, PyDoc_STR("Raises OSError") },
	{ "writelines", reader_writelines, METH_VARARGS, PyDoc_STR("Not implemented") },
	{ NULL, NULL }
};

PyTypeObject ZstdCompressionReaderType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.ZstdCompressionReader", /* tp_name */
	sizeof(ZstdCompressionReader), /* tp_basicsize */
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

void compressionreader_module_init(PyObject* mod) {
	/* TODO make reader a sub-class of io.RawIOBase */

	Py_TYPE(&ZstdCompressionReaderType) = &PyType_Type;
	if (PyType_Ready(&ZstdCompressionReaderType) < 0) {
		return;
	}
}
