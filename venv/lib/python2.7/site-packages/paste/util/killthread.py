"""
Kill a thread, from http://sebulba.wikispaces.com/recipe+thread2
"""
import types
try:
    import ctypes
except ImportError:
    raise ImportError(
        "You cannot use paste.util.killthread without ctypes installed")
if not hasattr(ctypes, 'pythonapi'):
    raise ImportError(
        "You cannot use paste.util.killthread without ctypes.pythonapi")

def async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed.

    tid is the value given by thread.get_ident() (an integer).
    Raise SystemExit to kill a thread."""
    if not isinstance(exctype, (types.ClassType, type)):
        raise TypeError("Only types can be raised (not instances)")
    if not isinstance(tid, int):
        raise TypeError("tid must be an integer")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")
