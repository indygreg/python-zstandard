/**
* Copyright (c) 2017-present, Gregory Szorc
* All rights reserved.
*
* This software may be modified and distributed under the terms
* of the BSD license. See the LICENSE file for details.
*/

#include "python-zstandard.h"

PyDoc_STRVAR(BufferWithSegments__doc__,
"BufferWithSegments - A memory buffer holding known sub-segments.\n"
"\n"
"This type represents a contiguous chunk of memory containing N discrete\n"
"items within sub-segments of that memory.\n"
"\n"
"Segments within the buffer are stored as an array of\n"
"``(offset, length)`` pairs, where each element is an unsigned 64-bit\n"
"integer using the host/native bit order representation.\n"
"\n"
"The type exists to facilitate operations against N>1 items without the\n"
"overhead of Python object creation and management.\n"
);

static void BufferWithSegments_dealloc(ZstdBufferWithSegments* self) {
	/* Backing memory is either canonically owned by a Py_buffer or by us. */
	if (self->parent.buf) {
		PyBuffer_Release(&self->parent);
		self->data = NULL;
	}
	else {
		PyMem_Free(self->data);
		self->data = NULL;
	}

	PyMem_Free(self->segments);
	self->segments = NULL;

	PyObject_Del(self);
}

static int BufferWithSegments_init(ZstdBufferWithSegments* self, PyObject* args, PyObject* kwargs) {
	static char* kwlist[] = {
		"data",
		"segments",
		NULL
	};

	Py_buffer segments;
	Py_ssize_t segmentCount;
	Py_ssize_t i;

	memset(&self->parent, 0, sizeof(self->parent));

#if PY_MAJOR_VERSION >= 3
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y*y*:BufferWithSegments",
#else
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s*s*:BufferWithSegments",
#endif
		kwlist, &self->parent, &segments)) {
		return -1;
	}

	if (!PyBuffer_IsContiguous(&self->parent, 'C') || self->parent.ndim > 1) {
		PyErr_SetString(PyExc_ValueError, "data buffer should be contiguous and have a single dimension");
		goto except;
	}

	if (!PyBuffer_IsContiguous(&segments, 'C') || segments.ndim > 1) {
		PyErr_SetString(PyExc_ValueError, "segments buffer should be contiguous and have a single dimension");
		goto except;
	}

	if (segments.len % sizeof(BufferSegment)) {
		PyErr_Format(PyExc_ValueError, "segments array size is not a multiple of %lu",
			sizeof(BufferSegment));
		goto except;
	}

	segmentCount = segments.len / sizeof(BufferSegment);

	/* Validate segments data, as blindly trusting it could lead to arbitrary
	memory access. */
	for (i = 0; i < segmentCount; i++) {
		BufferSegment* segment = &((BufferSegment*)(segments.buf))[i];

		if (segment->offset + segment->length > (unsigned long long)self->parent.len) {
			PyErr_SetString(PyExc_ValueError, "offset within segments array references memory outside buffer");
			goto except;
			return -1;
		}
	}

	/* Make a copy of the segments data. It is cheap to do so and is a guard
	   against caller changing offsets, which has security implications. */
	self->segments = PyMem_Malloc(segments.len);
	if (!self->segments) {
		PyErr_NoMemory();
		goto except;
	}

	memcpy(self->segments, segments.buf, segments.len);
	PyBuffer_Release(&segments);

	self->data = self->parent.buf;
	self->dataSize = self->parent.len;
	self->segmentCount = segmentCount;

	return 0;

except:
	PyBuffer_Release(&self->parent);
	PyBuffer_Release(&segments);
	return -1;
};

/**
 * Construct a BufferWithSegments from existing memory and offsets.
 *
 * Ownership of the backing memory and BufferSegments will be transferred to
 * the created object and freed when the BufferWithSegments is destroyed.
 */
ZstdBufferWithSegments* BufferWithSegments_FromMemory(void* data, unsigned long long dataSize,
	BufferSegment* segments, Py_ssize_t segmentsSize) {
	ZstdBufferWithSegments* result = NULL;
	Py_ssize_t i;

	if (NULL == data) {
		PyErr_SetString(PyExc_ValueError, "data is NULL");
		return NULL;
	}

	if (NULL == segments) {
		PyErr_SetString(PyExc_ValueError, "segments is NULL");
		return NULL;
	}

	for (i = 0; i < segmentsSize; i++) {
		BufferSegment* segment = &segments[i];

		if (segment->offset + segment->length > dataSize) {
			PyErr_SetString(PyExc_ValueError, "offset in segments overflows buffer size");
			return NULL;
		}
	}

	result = PyObject_New(ZstdBufferWithSegments, &ZstdBufferWithSegmentsType);
	if (NULL == result) {
		return NULL;
	}

	memset(&result->parent, 0, sizeof(result->parent));
	result->data = data;
	result->dataSize = dataSize;
	result->segments = segments;
	result->segmentCount = segmentsSize;

	return result;
}

static Py_ssize_t BufferWithSegments_length(ZstdBufferWithSegments* self) {
	return self->segmentCount;
}

static ZstdBufferSegment* BufferWithSegments_item(ZstdBufferWithSegments* self, Py_ssize_t i) {
	ZstdBufferSegment* result = NULL;

	if (i < 0) {
		PyErr_SetString(PyExc_IndexError, "offset must be non-negative");
		return NULL;
	}

	if (i >= self->segmentCount) {
		PyErr_Format(PyExc_IndexError, "offset must be less than %zd", self->segmentCount);
		return NULL;
	}

	result = (ZstdBufferSegment*)PyObject_CallObject((PyObject*)&ZstdBufferSegmentType, NULL);
	if (NULL == result) {
		return NULL;
	}

	result->parent = (PyObject*)self;
	Py_INCREF(self);

	result->data = (char*)self->data + self->segments[i].offset;
	result->dataSize = self->segments[i].length;
	result->offset = self->segments[i].offset;

	return result;
}

#if PY_MAJOR_VERSION >= 3
static int BufferWithSegments_getbuffer(ZstdBufferWithSegments* self, Py_buffer* view, int flags) {
	return PyBuffer_FillInfo(view, (PyObject*)self, self->data, self->dataSize, 1, flags);
}
#else
static Py_ssize_t BufferWithSegments_getreadbuffer(ZstdBufferWithSegments* self, Py_ssize_t segment, void **ptrptr) {
	if (segment != 0) {
		PyErr_SetString(PyExc_ValueError, "segment number must be 0");
		return -1;
	}

	*ptrptr = self->data;
	return self->dataSize;
}

static Py_ssize_t BufferWithSegments_getsegcount(ZstdBufferWithSegments* self, Py_ssize_t* len) {
	if (len) {
		*len = 1;
	}

	return 1;
}
#endif

PyDoc_STRVAR(BufferWithSegments_tobytes__doc__,
"Obtain a bytes instance for this buffer.\n"
);

static PyObject* BufferWithSegments_tobytes(ZstdBufferWithSegments* self) {
	return PyBytes_FromStringAndSize(self->data, self->dataSize);
}

PyDoc_STRVAR(BufferWithSegments_segments__doc__,
"Obtain a BufferSegments describing segments in this sintance.\n"
);

static ZstdBufferSegments* BufferWithSegments_segments(ZstdBufferWithSegments* self) {
	ZstdBufferSegments* result = (ZstdBufferSegments*)PyObject_CallObject((PyObject*)&ZstdBufferSegmentsType, NULL);
	if (NULL == result) {
		return NULL;
	}

	result->parent = (PyObject*)self;
	Py_INCREF(self);
	result->segments = self->segments;
	result->segmentCount = self->segmentCount;

	return result;
}

static PySequenceMethods BufferWithSegments_sq = {
	(lenfunc)BufferWithSegments_length, /* sq_length */
	0, /* sq_concat */
	0, /* sq_repeat */
	(ssizeargfunc)BufferWithSegments_item, /* sq_item */
	0, /* sq_ass_item */
	0, /* sq_contains */
	0, /* sq_inplace_concat */
	0 /* sq_inplace_repeat */
};

static PyBufferProcs BufferWithSegments_as_buffer = {
#if PY_MAJOR_VERSION >= 3
	(getbufferproc)BufferWithSegments_getbuffer, /* bf_getbuffer */
	0 /* bf_releasebuffer */
#else
	(readbufferproc)BufferWithSegments_getreadbuffer, /* bf_getreadbuffer */
	0, /* bf_getwritebuffer */
	(segcountproc)BufferWithSegments_getsegcount, /* bf_getsegcount */
	0 /* bf_getcharbuffer */
#endif
};

static PyMethodDef BufferWithSegments_methods[] = {
	{ "segments", (PyCFunction)BufferWithSegments_segments,
	  METH_NOARGS, BufferWithSegments_segments__doc__ },
	{ "tobytes", (PyCFunction)BufferWithSegments_tobytes,
	  METH_NOARGS, BufferWithSegments_tobytes__doc__ },
	{ NULL, NULL }
};

static PyMemberDef BufferWithSegments_members[] = {
	{ "size", T_ULONGLONG, offsetof(ZstdBufferWithSegments, dataSize),
	  READONLY, "total size of the buffer in bytes" },
	{ NULL }
};

PyTypeObject ZstdBufferWithSegmentsType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.BufferWithSegments", /* tp_name */
	sizeof(ZstdBufferWithSegments),/* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)BufferWithSegments_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	&BufferWithSegments_sq,    /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	&BufferWithSegments_as_buffer, /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	BufferWithSegments__doc__, /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	BufferWithSegments_methods, /* tp_methods */
	BufferWithSegments_members, /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	(initproc)BufferWithSegments_init, /* tp_init */
	0,                         /* tp_alloc */
	PyType_GenericNew,         /* tp_new */
};

PyDoc_STRVAR(BufferSegments__doc__,
"BufferSegments - Represents segments/offsets within a BufferWithSegments\n"
);

static void BufferSegments_dealloc(ZstdBufferSegments* self) {
	Py_CLEAR(self->parent);
	PyObject_Del(self);
}

#if PY_MAJOR_VERSION >= 3
static int BufferSegments_getbuffer(ZstdBufferSegments* self, Py_buffer* view, int flags) {
	return PyBuffer_FillInfo(view, (PyObject*)self,
		(void*)self->segments, self->segmentCount * sizeof(BufferSegment),
		1, flags);
}
#else
static Py_ssize_t BufferSegments_getreadbuffer(ZstdBufferSegments* self, Py_ssize_t segment, void **ptrptr) {
	if (segment != 0) {
		PyErr_SetString(PyExc_ValueError, "segment number must be 0");
		return -1;
	}

	*ptrptr = (void*)self->segments;
	return self->segmentCount * sizeof(BufferSegment);
}

static Py_ssize_t BufferSegments_getsegcount(ZstdBufferSegments* self, Py_ssize_t* len) {
	if (len) {
		*len = 1;
	}

	return 1;
}
#endif

static PyBufferProcs BufferSegments_as_buffer = {
#if PY_MAJOR_VERSION >= 3
	(getbufferproc)BufferSegments_getbuffer,
	0
#else
	(readbufferproc)BufferSegments_getreadbuffer,
	0,
	(segcountproc)BufferSegments_getsegcount,
	0
#endif
};

PyTypeObject ZstdBufferSegmentsType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.BufferSegments", /* tp_name */
	sizeof(ZstdBufferSegments),/* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)BufferSegments_dealloc, /* tp_dealloc */
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
	&BufferSegments_as_buffer, /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	BufferSegments__doc__,     /* tp_doc */
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
	PyType_GenericNew,         /* tp_new */
};

PyDoc_STRVAR(BufferSegment__doc__,
	"BufferSegment - Represents a segment within a BufferWithSegments\n"
);

static void BufferSegment_dealloc(ZstdBufferSegment* self) {
	Py_CLEAR(self->parent);
	PyObject_Del(self);
}

static Py_ssize_t BufferSegment_length(ZstdBufferSegment* self) {
	return self->dataSize;
}

#if PY_MAJOR_VERSION >= 3
static int BufferSegment_getbuffer(ZstdBufferSegment* self, Py_buffer* view, int flags) {
	return PyBuffer_FillInfo(view, (PyObject*)self,
		self->data, self->dataSize, 1, flags);
}
#else
static Py_ssize_t BufferSegment_getreadbuffer(ZstdBufferSegment* self, Py_ssize_t segment, void **ptrptr) {
	if (segment != 0) {
		PyErr_SetString(PyExc_ValueError, "segment number must be 0");
		return -1;
	}

	*ptrptr = self->data;
	return self->dataSize;
}

static Py_ssize_t BufferSegment_getsegcount(ZstdBufferSegment* self, Py_ssize_t* len) {
	if (len) {
		*len = 1;
	}

	return 1;
}
#endif

PyDoc_STRVAR(BufferSegment_tobytes__doc__,
"Obtain a bytes instance for this segment.\n"
);

static PyObject* BufferSegment_tobytes(ZstdBufferSegment* self) {
	return PyBytes_FromStringAndSize(self->data, self->dataSize);
}

static PySequenceMethods BufferSegment_sq = {
	(lenfunc)BufferSegment_length, /* sq_length */
	0, /* sq_concat */
	0, /* sq_repeat */
	0, /* sq_item */
	0, /* sq_ass_item */
	0, /* sq_contains */
	0, /* sq_inplace_concat */
	0 /* sq_inplace_repeat */
};

static PyBufferProcs BufferSegment_as_buffer = {
#if PY_MAJOR_VERSION >= 3
	(getbufferproc)BufferSegment_getbuffer,
	0
#else
	(readbufferproc)BufferSegment_getreadbuffer,
	0,
	(segcountproc)BufferSegment_getsegcount,
	0
#endif
};

static PyMethodDef BufferSegment_methods[] = {
	{ "tobytes", (PyCFunction)BufferSegment_tobytes,
	  METH_NOARGS, BufferSegment_tobytes__doc__ },
	{ NULL, NULL }
};

static PyMemberDef BufferSegment_members[] = {
	{ "offset", T_ULONGLONG, offsetof(ZstdBufferSegment, offset), READONLY,
	  "offset of segment within parent buffer" },
	  { NULL }
};

PyTypeObject ZstdBufferSegmentType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"zstd.BufferSegment", /* tp_name */
	sizeof(ZstdBufferSegment),/* tp_basicsize */
	0,                         /* tp_itemsize */
	(destructor)BufferSegment_dealloc, /* tp_dealloc */
	0,                         /* tp_print */
	0,                         /* tp_getattr */
	0,                         /* tp_setattr */
	0,                         /* tp_compare */
	0,                         /* tp_repr */
	0,                         /* tp_as_number */
	&BufferSegment_sq,         /* tp_as_sequence */
	0,                         /* tp_as_mapping */
	0,                         /* tp_hash  */
	0,                         /* tp_call */
	0,                         /* tp_str */
	0,                         /* tp_getattro */
	0,                         /* tp_setattro */
	&BufferSegment_as_buffer,  /* tp_as_buffer */
	Py_TPFLAGS_DEFAULT,        /* tp_flags */
	BufferSegment__doc__,      /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	BufferSegment_methods,     /* tp_methods */
	BufferSegment_members,     /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	PyType_GenericNew,         /* tp_new */
};

void bufferutil_module_init(PyObject* mod) {
	Py_TYPE(&ZstdBufferWithSegmentsType) = &PyType_Type;
	if (PyType_Ready(&ZstdBufferWithSegmentsType) < 0) {
		return;
	}

	Py_INCREF(&ZstdBufferWithSegmentsType);
	PyModule_AddObject(mod, "BufferWithSegments", (PyObject*)&ZstdBufferWithSegmentsType);

	Py_TYPE(&ZstdBufferSegmentsType) = &PyType_Type;
	if (PyType_Ready(&ZstdBufferSegmentsType) < 0) {
		return;
	}

	Py_INCREF(&ZstdBufferSegmentsType);
	PyModule_AddObject(mod, "BufferSegments", (PyObject*)&ZstdBufferSegmentsType);

	Py_TYPE(&ZstdBufferSegmentType) = &PyType_Type;
	if (PyType_Ready(&ZstdBufferSegmentType) < 0) {
		return;
	}

	Py_INCREF(&ZstdBufferSegmentType);
	PyModule_AddObject(mod, "BufferSegment", (PyObject*)&ZstdBufferSegmentType);
}
