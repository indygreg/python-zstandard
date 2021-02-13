/* ----------------------------
     BlocksOutputBuffer code
   ---------------------------- */

#ifndef BLOCKS_OUTPUT_BUFFER_H
#define BLOCKS_OUTPUT_BUFFER_H

typedef struct {
    /* List of blocks */
    PyObject *list;
    /* Number of whole allocated size. */
    Py_ssize_t allocated;
    /* Max length of the buffer, negative number for unlimited length. */
    Py_ssize_t max_length;
} BlocksOutputBuffer;

#ifndef Py_UNREACHABLE
    #define Py_UNREACHABLE() assert(0)
#endif

#if defined(__GNUC__)
#  define UNUSED_ATTR __attribute__((unused))
#else
#  define UNUSED_ATTR
#endif

static const char unable_allocate_msg[] = "Unable to allocate output buffer.";

/* Block size sequence. Below functions assume the type is int. */
#define KiB (1024)
#define MiB (1024*1024)
static const int BUFFER_BLOCK_SIZE[] =
    { 32*KiB, 64*KiB, 256*KiB, 1*MiB, 4*MiB, 8*MiB, 16*MiB, 16*MiB,
      32*MiB, 32*MiB, 32*MiB, 32*MiB, 64*MiB, 64*MiB, 128*MiB, 128*MiB,
      256*MiB };
#undef KiB
#undef MiB

/* According to the block sizes defined by BUFFER_BLOCK_SIZE, the whole
   allocated size growth step is:
    1   32 KiB       +32 KiB
    2   96 KiB       +64 KiB
    3   352 KiB      +256 KiB
    4   1.34 MiB     +1 MiB
    5   5.34 MiB     +4 MiB
    6   13.34 MiB    +8 MiB
    7   29.34 MiB    +16 MiB
    8   45.34 MiB    +16 MiB
    9   77.34 MiB    +32 MiB
    10  109.34 MiB   +32 MiB
    11  141.34 MiB   +32 MiB
    12  173.34 MiB   +32 MiB
    13  237.34 MiB   +64 MiB
    14  301.34 MiB   +64 MiB
    15  429.34 MiB   +128 MiB
    16  557.34 MiB   +128 MiB
    17  813.34 MiB   +256 MiB
    18  1069.34 MiB  +256 MiB
    19  1325.34 MiB  +256 MiB
    20  1581.34 MiB  +256 MiB
    21  1837.34 MiB  +256 MiB
    22  2093.34 MiB  +256 MiB
    ...
*/

/* Initialize the buffer, and grow the buffer.
   max_length: Max length of the buffer, -1 for unlimited length.
   Return 0 on success
   Return -1 on failure
*/
static UNUSED_ATTR int
OutputBuffer_InitAndGrow(BlocksOutputBuffer *buffer, ZSTD_outBuffer *ob,
                         Py_ssize_t max_length)
{
    PyObject *b;
    int block_size;

    /* Set & check max_length */
    buffer->max_length = max_length;
    if (0 <= max_length && max_length < BUFFER_BLOCK_SIZE[0]) {
        block_size = (int) max_length;
    } else {
        block_size = BUFFER_BLOCK_SIZE[0];
    }

    /* The first block */
    b = PyBytes_FromStringAndSize(NULL, block_size);
    if (b == NULL) {
        buffer->list = NULL; /* For OutputBuffer_OnError() */
        return -1;
    }

    /* Create the list */
    buffer->list = PyList_New(1);
    if (buffer->list == NULL) {
        Py_DECREF(b);
        return -1;
    }
    PyList_SET_ITEM(buffer->list, 0, b);

    /* Set variables */
    buffer->allocated = block_size;

    ob->dst = PyBytes_AS_STRING(b);
    ob->size = block_size;
    ob->pos = 0;
    return 0;
}

/* Initialize the buffer, with an initial size.
   init_size: the initial size.
   Return 0 on success
   Return -1 on failure
*/
static UNUSED_ATTR int
OutputBuffer_InitWithSize(BlocksOutputBuffer *buffer, ZSTD_outBuffer *ob,
                          Py_ssize_t init_size)
{
    PyObject *b;

    /* The first block */
    b = PyBytes_FromStringAndSize(NULL, init_size);
    if (b == NULL) {
        buffer->list = NULL; /* For OutputBuffer_OnError() */
        PyErr_SetString(PyExc_MemoryError, unable_allocate_msg);
        return -1;
    }

    /* Create the list */
    buffer->list = PyList_New(1);
    if (buffer->list == NULL) {
        Py_DECREF(b);
        return -1;
    }
    PyList_SET_ITEM(buffer->list, 0, b);

    /* Set variables */
    buffer->allocated = init_size;
    buffer->max_length = -1;

    ob->dst = PyBytes_AS_STRING(b);
    ob->size = (size_t) init_size;
    ob->pos = 0;
    return 0;
}

/* Grow the buffer. The avail_out must be 0, please check it before calling.
   Return 0 on success
   Return -1 on failure
*/
static UNUSED_ATTR int
OutputBuffer_Grow(BlocksOutputBuffer *buffer, ZSTD_outBuffer *ob)
{
    PyObject *b;
    const Py_ssize_t list_len = Py_SIZE(buffer->list);
    int block_size;

    /* Ensure no gaps in the data */
    assert(ob->pos == ob->size);

    /* Get block size */
    if (list_len < (Py_ssize_t) Py_ARRAY_LENGTH(BUFFER_BLOCK_SIZE)) {
        block_size = BUFFER_BLOCK_SIZE[list_len];
    } else {
        block_size = BUFFER_BLOCK_SIZE[Py_ARRAY_LENGTH(BUFFER_BLOCK_SIZE) - 1];
    }

    /* Check max_length */
    if (buffer->max_length >= 0) {
        /* Prevent adding unlimited number of empty bytes to the list */
        if (buffer->max_length == 0) {
            assert(ob->pos == ob->size);
            return 0;
        }
        /* block_size of the last block */
        if (block_size > buffer->max_length - buffer->allocated) {
            block_size = (int) (buffer->max_length - buffer->allocated);
        }
    }

    /* Check buffer->allocated overflow */
    if (block_size > PY_SSIZE_T_MAX - buffer->allocated) {
        PyErr_SetString(PyExc_MemoryError, unable_allocate_msg);
        return -1;
    }

    /* Create the block */
    b = PyBytes_FromStringAndSize(NULL, block_size);
    if (b == NULL) {
        PyErr_SetString(PyExc_MemoryError, unable_allocate_msg);
        return -1;
    }
    if (PyList_Append(buffer->list, b) < 0) {
        Py_DECREF(b);
        return -1;
    }
    Py_DECREF(b);

    /* Set variables */
    buffer->allocated += block_size;

    ob->dst = PyBytes_AS_STRING(b);
    ob->size = block_size;
    ob->pos = 0;
    return 0;
}

/* Whether the output data has reached max_length.
   The avail_out must be 0, please check it before calling. */
static inline UNUSED_ATTR int
OutputBuffer_ReachedMaxLength(BlocksOutputBuffer *buffer, ZSTD_outBuffer *ob)
{
    /* Ensure (data size == allocated size) */
    assert(ob->pos == ob->size);

    return buffer->allocated == buffer->max_length;
}

/* Finish the buffer.
   Return a bytes object on success
   Return NULL on failure
*/
static UNUSED_ATTR PyObject *
OutputBuffer_Finish(BlocksOutputBuffer *buffer, ZSTD_outBuffer *ob)
{
    PyObject *result, *block;
    const Py_ssize_t list_len = Py_SIZE(buffer->list);

    /* Fast path for single block */
    if ((list_len == 1 && ob->pos == ob->size) ||
        (list_len == 2 && ob->pos == 0)) {
        block = PyList_GET_ITEM(buffer->list, 0);
        Py_INCREF(block);

        Py_DECREF(buffer->list);
        return block;
    }

    /* Final bytes object */
    result = PyBytes_FromStringAndSize(NULL, buffer->allocated - (ob->size - ob->pos));
    if (result == NULL) {
        PyErr_SetString(PyExc_MemoryError, unable_allocate_msg);
        return NULL;
    }

    /* Memory copy */
    if (list_len > 0) {
        char *posi = PyBytes_AS_STRING(result);

        /* Blocks except the last one */
        Py_ssize_t i = 0;
        for (; i < list_len-1; i++) {
            block = PyList_GET_ITEM(buffer->list, i);
            memcpy(posi, PyBytes_AS_STRING(block), Py_SIZE(block));
            posi += Py_SIZE(block);
        }
        /* The last block */
        block = PyList_GET_ITEM(buffer->list, i);
        memcpy(posi, PyBytes_AS_STRING(block), ob->pos);
    } else {
        /* buffer->list has at least one block, see initialize functions. */
        Py_UNREACHABLE();
    }

    Py_DECREF(buffer->list);
    return result;
}

/* Clean up the buffer */
static inline UNUSED_ATTR void
OutputBuffer_OnError(BlocksOutputBuffer *buffer)
{
    Py_XDECREF(buffer->list);
}

#endif