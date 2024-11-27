/*
 * Provides wrappers around C11 standard library atomics and MSVC intrinsics
 * to provide basic atomic load and store functionality. This is based on
 * code in CPython's pyatomic.h, pyatomic_std.h, and pyatomic_msc.h
 *
 * Adapted from:
 * - numpy/_core/src/common/npy_atomic.h
 * - cpython/Include/cpython/pyatomic.h
 */

#ifndef PYZSTD_ATOMICS_H
#define PYZSTD_ATOMICS_H

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L \
    && !defined(__STDC_NO_ATOMICS__)
// TODO: support C++ atomics as well if this header is ever needed in C++
    #include <stdatomic.h>
    #include <stdint.h>
    #define STDC_ATOMICS
#elif _MSC_VER
    #include <intrin.h>
    #define MSC_ATOMICS
    #if !defined(_M_X64) && !defined(_M_IX86) && !defined(_M_ARM64)
        #error "Unsupported MSVC build configuration, neither x86 or ARM"
    #endif
#elif defined(__GNUC__) && (__GNUC__ > 4)
    #define GCC_ATOMICS
#elif defined(__clang__)
    #if __has_builtin(__atomic_load)
        #define GCC_ATOMICS
    #endif
#else
    #error "no supported atomic implementation for this platform/compiler"
#endif


static inline int8_t
pyzstd_atomic_load_int8(const int8_t *obj) {
#ifdef STDC_ATOMICS
    return (int8_t)atomic_load((const _Atomic(int8_t)*)obj);
#elif defined(MSC_ATOMICS)
#if defined(_M_X64) || defined(_M_IX86)
    return *(volatile int8_t *)obj;
#else // defined(_M_ARM64)
    return (int8_t)__ldar8((unsigned __int8 volatile *)obj);
#endif
#elif defined(GCC_ATOMICS)
    return __atomic_load_n(obj, __ATOMIC_SEQ_CST);
#endif
}

static inline void
pyzstd_atomic_store_int8(int8_t *obj, int8_t value) {
#ifdef STDC_ATOMICS
    atomic_store((_Atomic(int8_t)*)obj, value);
#elif defined(MSC_ATOMICS)
    _InterlockedExchange8((volatile char *)obj, (char)value);
#elif defined(GCC_ATOMICS)
    __atomic_store_n(obj, value, __ATOMIC_SEQ_CST);
#endif
}

static inline int
pyzstd_atomic_compare_exchange_int8(int8_t *obj, int8_t expected, int8_t desired) {
#ifdef STDC_ATOMICS
    return atomic_compare_exchange_strong((_Atomic(int8_t)*)obj,
                                          &expected, desired);
#elif defined(MSC_ATOMICS)
    int8_t initial = (int8_t)_InterlockedCompareExchange8(
                                       (volatile char *)obj,
                                       (char)value,
                                       (char)expected);
    if (initial == *expected) {
        return 1;
    }
    *expected = initial;
    return 0;
#elif defined(GCC_ATOMICS)
    return __atomic_compare_exchange_n(obj, &expected, desired, 0,
                                       __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);
#endif
}

#undef MSC_ATOMICS
#undef STDC_ATOMICS
#undef GCC_ATOMICS

#endif // PYZSTD_ATOMICS_H
