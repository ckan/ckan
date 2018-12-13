from __future__ import absolute_import
import sys

# True if we are running on Python 2.
PY2 = sys.version_info[0] == 2
PYVER = sys.version_info[:2]
JYTHON = sys.platform.startswith('java')

if PY2 and not JYTHON:  # pragma: no cover
    import cPickle as pickle
else:  # pragma: no cover
    import pickle


if not PY2:  # pragma: no cover
    xrange_ = range
    NoneType = type(None)

    string_type = str
    unicode_text = str
    byte_string = bytes

    from urllib.parse import urlencode as url_encode
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
    from urllib.parse import urlparse as url_parse
    from urllib.request import url2pathname
    import http.cookies as http_cookies
    from base64 import b64decode as _b64decode, b64encode as _b64encode

    try:
        import dbm as anydbm
    except:
        import dumbdbm as anydbm

    def b64decode(b):
        return _b64decode(b.encode('ascii'))

    def b64encode(s):
        return _b64encode(s).decode('ascii')

    def u_(s):
        return str(s)

    def bytes_(s):
        if isinstance(s, byte_string):
            return s
        return str(s).encode('ascii', 'strict')

    def dictkeyslist(d):
        return list(d.keys())

else:
    xrange_ = xrange
    from types import NoneType

    string_type = basestring
    unicode_text = unicode
    byte_string = str

    from urllib import urlencode as url_encode
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urlparse import urlparse as url_parse
    from urllib import url2pathname
    import Cookie as http_cookies
    from base64 import b64decode, b64encode
    import anydbm

    def u_(s):
        if isinstance(s, unicode_text):
            return s

        if not isinstance(s, byte_string):
            s = str(s)
        return unicode(s, 'utf-8')

    def bytes_(s):
        if isinstance(s, byte_string):
            return s
        return str(s)

    def dictkeyslist(d):
        return d.keys()


def im_func(f):
    if not PY2:  # pragma: no cover
        return getattr(f, '__func__', None)
    else:
        return getattr(f, 'im_func', None)


def default_im_func(f):
    if not PY2:  # pragma: no cover
        return getattr(f, '__func__', f)
    else:
        return getattr(f, 'im_func', f)


def im_self(f):
    if not PY2:  # pragma: no cover
        return getattr(f, '__self__', None)
    else:
        return getattr(f, 'im_self', None)


def im_class(f):
    if not PY2:  # pragma: no cover
        self = im_self(f)
        if self is not None:
            return self.__class__
        else:
            return None
    else:
        return getattr(f, 'im_class', None)


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


if not PY2:  # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value
else:  # pragma: no cover
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


try:
    from inspect import signature as func_signature
except ImportError:
    from funcsigs import signature as func_signature


def bindfuncargs(arginfo, args, kwargs):
    boundargs = arginfo.bind(*args, **kwargs)
    return boundargs.args, boundargs.kwargs
