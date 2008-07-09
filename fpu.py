"""Floating-point unit control and helper functions.

This module provides:

  1. Mechanisms for the control of the FPU's rounding modes;

  2. Helper functions that respect IEEE 754 semantics.

Limitations
    The current implementation of the FPU's rounding-mode control is
    thought to be not thread-safe.
"""

def _init_libm():
    "Initialize low-level FPU control using C99 primitives in libm."
    global _fe_upward, _fe_downward, _fegetround, _fesetround

    import platform
    processor = platform.processor()
    if processor == 'powerpc':
        _fe_upward, _fe_downward = 2, 3
    elif processor == 'sparc':
        _fe_upward, _fe_downward = 0x80000000, 0xC0000000
    else:
        _fe_upward, _fe_downward = 0x0800, 0x0400

    from ctypes import cdll
    from ctypes.util import find_library
    libm = cdll.LoadLibrary(find_library('m'))
    _fegetround, _fesetround = libm.fegetround, libm.fesetround


def _init_msvc():
    "Initialize low-level FPU control using the Microsoft VC runtime."
    global _fe_upward, _fe_downward, setup, _fegetround, _fesetround

    from ctypes import cdll
    global _controlfp
    _controlfp = cdll.msvcrt._controlfp
    _fe_upward, _fe_downward = 0x0200, 0x0100
    def _fegetround():
        return _controlfp(0, 0)
    def _fesetround(flag):
        _controlfp(flag, 0x300)


for _f in _init_libm, _init_msvc:
    try:
        _f()
        break
    except:
        pass
else:
    import warnings
    warnings.warn("Cannot determine FPU control primitives. The fpu module is not correcly initialized.", stacklevel=2)
try:
    del _f
except:
    pass


from numpy import nan, infty as infinity, finfo
finfo = finfo(float)


def isnan(x):
    "Return True if x is nan."
    return x != x


def nudge(x, dir):
    "Nudge a float in the specified direction (dir = +1 or -1)."
    assert dir in (-1, +1)
    import math
    f = dir * 2 ** (math.frexp(x)[1] - 1)
    y = x + f * finfo.epsneg
    if y != x:
        return y
    else:
        return x + f * finfo.eps


def down(f):
    "Perform a computation with the FPU rounding downwards."
    saved = _fegetround()
    try:
        _fesetround(_fe_downward)
        return f()
    finally:
        _fesetround(saved)


def up(f):
    "Perform a computation with the FPU rounding upwards."
    saved = _fegetround()
    try:
        _fesetround(_fe_upward)
        return f()
    finally:
        _fesetround(saved)


class NanException(ValueError):
    "Exception thrown when an unwanted nan is encountered."
    pass


def ensure_nonan(x):
    "Return x, throwing a NanException if x is nan."
    if isnan(x):
        raise NanException
    return x


def min(l):
    "Return the minimum of the elements in l, or nan if any element is nan."
    import __builtin__
    try:
        return __builtin__.min(ensure_nonan(x) for x in l)
    except NanException:
        return nan


def max(l):
    "Return the maximum of the elements in l, or nan if any element is nan."
    import __builtin__
    try:
        return __builtin__.max(ensure_nonan(x) for x in l)
    except NanException:
        return nan


def power(x, n):
    "Raise x to the n-th power with correct rounding."

    if not isinstance(n, (int, long)):
        return x ** n
    if n < 0:
        return 1/power(x, -n)
    l=();
    while n > 0:
        n, y= divmod(n, 2)
        l=(y, l)
    result = 1
    while l:
        y, l = l
        if y:
            result = result * result * x
        else:
            result = result * result
    return result


def intrepr(x):
    "Return the interger pair (n, k) such that x = n * 2 ** k."
    import math
    m, e = math.frexp(x)
    return int(m * 2 ** (finfo.nmant + 1)), e - (finfo.nmant + 1)