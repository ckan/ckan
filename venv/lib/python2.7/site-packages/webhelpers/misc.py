"""Helpers that are neither text, numeric, container, or date.
"""

import itertools
import traceback
import types
import warnings

def all(seq, pred=None):
    """Is ``pred(elm)`` true for all elements?

    With the default predicate, this is the same as Python 2.5's ``all()``
    function; i.e., it returns true if all elements are true.

    >>> all(["A", "B"])
    True
    >>> all(["A", ""])
    False
    >>> all(["", ""])
    False
    >>> all(["A", "B", "C"], lambda x: x <= "C")
    True
    >>> all(["A", "B", "C"], lambda x: x < "C")
    False

    From recipe in itertools docs.
    """
    for elm in itertools.ifilterfalse(pred, seq):
        return False
    return True

def any(seq, pred=None):
    """Is ``pred(elm)`` is true for any element?

    With the default predicate, this is the same as Python 2.5's ``any()``
    function; i.e., it returns true if any element is true.

    >>> any(["A", "B"])
    True
    >>> any(["A", ""])
    True
    >>> any(["", ""])
    False
    >>> any(["A", "B", "C"], lambda x: x <= "C")
    True
    >>> any(["A", "B", "C"], lambda x: x < "C")
    True

    From recipe in itertools docs.
    """
    for elm in itertools.ifilter(pred, seq):
        return True
    return False

def no(seq, pred=None):
    """Is ``pred(elm)`` false for all elements?

    With the default predicate, this returns true if all elements are false.

    >>> no(["A", "B"])
    False
    >>> no(["A", ""])
    False
    >>> no(["", ""])
    True
    >>> no(["A", "B", "C"], lambda x: x <= "C")
    False
    >>> no(["X", "Y", "Z"], lambda x: x <="C")
    True

    From recipe in itertools docs.
    """
    for elm in itertools.ifilter(pred, seq):
        return False
    return True

def count_true(seq, pred=lambda x: x):
    """How many elements is ``pred(elm)`` true for?

    With the default predicate, this counts the number of true elements.

    >>> count_true([1, 2, 0, "A", ""])
    3
    >>> count_true([1, "A", 2], lambda x: isinstance(x, int))
    2

    This is equivalent to the ``itertools.quantify`` recipe, which I couldn't
    get to work.
    """
    ret = 0
    for x in seq:
        if pred(x):
            ret += 1
    return ret

def convert_or_none(value, type_):
    """Return the value converted to the type, or None if error.

    ``type_`` may be a Python type or any function taking one argument.

    >>> print convert_or_none("5", int)
    5
    >>> print convert_or_none("A", int)
    None
    """
    try:
        return type_(value)
    except Exception:
        return None

def flatten(iterable):
    """Recursively iterate lists and tuples.

    Examples:

    >>> list(flatten([1, [2, 3], 4]))
    [1, 2, 3, 4]
    >>> list(flatten([1, (2, 3, [4]), 5]))
    [1, 2, 3, 4, 5]
    """
    for elm in iterable:
        if isinstance(elm, (list, tuple)):
            for relm in flatten(elm):
                yield relm
        else:
            yield elm



def subclasses_only(class_, it, exclude=None):
    """Extract the subclasses of a class from a module, dict, or iterable.

    Return a list of subclasses found. The class itself will not be included.
    This is useful to collect the concrete subclasses of an abstract base
    class.

    ``class_`` is a class.

    ``it`` is a dict or iterable. If a dict is passed, examine its values,
    not its keys. To introspect the current module, pass ``globals()``. To
    introspect another module or namespace, pass
    ``vars(the_module_or_namespace)``.

    ``exclude`` is an optional list of additional classes to ignore. 
    This is mainly used to exclude abstract subclasses.
    """
    if isinstance(it, dict):
        it = it.itervalues()
    class_types = (type, types.ClassType)
    ignore = [class_]
    if exclude:
        ignore.extend(exclude)
    return [x for x in it if isinstance(x, class_types) and 
        issubclass(x, class_) and x not in ignore]


class NotGiven(object):
    """A default value for function args.

    Use this when you need to distinguish between ``None`` and no value.
    
    Example::
    
        >>> def foo(arg=NotGiven):
        ...     print arg is NotGiven
        ...
        >>> foo()
        True
        >>> foo(None)
        False

    """
    pass


class DeclarativeException(Exception):
    """A simpler way to define an exception with a fixed message.

    Subclasses have a class attribute ``.message``, which is used if no
    message is passed to the constructor. The default message is the empty
    string.

    Example::

        >>> class MyException(DeclarativeException):
        ...     message="can't frob the bar when foo is enabled"
        ...
        >>> try:
        ...     raise MyException()
        ... except Exception, e:
        ...      print e
        ...
        can't frob the bar when foo is enabled
    """
    message = ""

    def __init__(self, message=None):
        Exception.__init__(self, message or self.message)


class OverwriteError(Exception):
    """Refusing to overwrite an existing file or directory."""

    def __init__(self, filename, message="not overwriting '%s'"):
        message %= (filename,)
        Exception.__init__(self, message)
        self.filename = filename

def format_exception(exc=None):
    """Format the exception type and value for display, without the traceback.

    This is the function you always wished were in the ``traceback`` module but
    isn't. It's *different* from ``traceback.format_exception``, which includes
    the traceback, returns a list of lines, and has a trailing newline.

    If you don't provide an exception object as an argument, it will call
    ``sys.exc_info()`` to get the current exception.
    """
    if exc:
        exc_type = type(exc)
    else:
        exc_type, exc = sys.exc_info()[:2]
    lines = traceback.format_exception_only(exc_type, exc)
    return "".join(lines).rstrip()

def deprecate(message, pending=False, stacklevel=2):
    """Issue a deprecation warning.

    ``message``: the deprecation message.

    ``pending``: if true, use ``PendingDeprecationWarning``. If false (default), 
    use ``DeprecationWarning``. Python displays deprecations and ignores
    pending deprecations by default.

    ``stacklevel``: passed to ``warnings.warn``. The default level 2 makes the
    traceback end at the caller's level. Higher numbers make it end at higher
    levels.
    """
    category = pending and PendingDeprecationWarning or DeprecationWarning
    warnings.warn(message, category, stacklevel)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
