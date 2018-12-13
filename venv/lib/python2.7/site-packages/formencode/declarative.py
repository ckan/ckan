"""
Declarative objects for FormEncode.

Declarative objects have a simple protocol: you can use classes in
lieu of instances and they are equivalent, and any keyword arguments
you give to the constructor will override those instance variables.
(So if a class is received, we'll simply instantiate an instance with
no arguments).

You can provide a variable __unpackargs__ (a list of strings), and if
the constructor is called with non-keyword arguments they will be
interpreted as the given keyword arguments.

If __unpackargs__ is ('*', name), then all the arguments will be put
in a variable by that name.

Also, you can define a __classinit__(cls, new_attrs) method, which
will be called when the class is created (including subclasses).
"""

import copy
import types

from itertools import count


class classinstancemethod(object):
    """
    Acts like a class method when called from a class, like an
    instance method when called by an instance.  The method should
    take two arguments, 'self' and 'cls'; one of these will be None
    depending on how the method was called.
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls=None):
        return _methodwrapper(self.func, obj=obj, cls=cls)


class _methodwrapper(object):

    def __init__(self, func, obj, cls):
        self.func = func
        self.obj = obj
        self.cls = cls

    def __call__(self, *args, **kw):
        assert 'self' not in kw and 'cls' not in kw, (
            "You cannot use 'self' or 'cls' arguments to a "
            "classinstancemethod")
        return self.func(*((self.obj, self.cls) + args), **kw)

    def __repr__(self):
        if self.obj is None:
            return ('<bound class method %s.%s>'
                    % (self.cls.__name__, self.func.func_name))
        return ('<bound method %s.%s of %r>'
                % (self.cls.__name__, self.func.func_name, self.obj))


class DeclarativeMeta(type):

    def __new__(meta, class_name, bases, new_attrs):
        cls = type.__new__(meta, class_name, bases, new_attrs)
        for name in cls.__mutableattributes__:
            setattr(cls, name, copy.copy(getattr(cls, name)))
        cls.declarative_count = cls.counter.next()
        if ('__classinit__' in new_attrs and not isinstance(cls.__classinit__,
                (staticmethod, types.FunctionType))):
            setattr(cls, '__classinit__',
                    staticmethod(cls.__classinit__.im_func))
        cls.__classinit__(cls, new_attrs)
        names = getattr(cls, '__singletonmethods__', None)
        if names:
            for name in names:
                meth = cls.__dict__.get(name)
                if meth and not isinstance(meth, singletonmethod):
                    setattr(cls, name, singletonmethod(meth))
        return cls


class singletonmethod(object):
    """
    For Declarative subclasses, this decorator will call the method
    on the cls.singleton() object if called as a class method (or
    as normal if called as an instance method).
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls=None):
        if obj is None:
            obj = cls.singleton()
        return types.MethodType(self.func, obj)


class Declarative(object):

    __unpackargs__ = ()

    __mutableattributes__ = ()

    __metaclass__ = DeclarativeMeta

    __singletonmethods__ = ()

    counter = count()

    @staticmethod
    def __classinit__(cls, new_attrs):
        pass

    def __init__(self, *args, **kw):
        if self.__unpackargs__ and self.__unpackargs__[0] == '*':
            assert len(self.__unpackargs__) == 2, (
                "When using __unpackargs__ = ('*', varname),"
                " you must only provide a single variable name"
                " (you gave %r)" % self.__unpackargs__)
            name = self.__unpackargs__[1]
            if name in kw:
                if args:
                    raise TypeError(
                        "keyword parameter '%s' was given by position and name"
                        % name)
            else:
                kw[name] = args
        else:
            if len(args) > len(self.__unpackargs__):
                raise TypeError(
                    '%s() takes at most %i arguments (%i given)'
                    % (self.__class__.__name__,
                       len(self.__unpackargs__),
                       len(args)))
            for name, arg in zip(self.__unpackargs__, args):
                if name in kw:
                    raise TypeError(
                        "keyword parameter '%s' was given by position and name"
                        % name)
                kw[name] = arg
        for name in self.__mutableattributes__:
            if name not in kw:
                setattr(self, name, copy.copy(getattr(self, name)))
        for name, value in kw.iteritems():
            setattr(self, name, value)
        if 'declarative_count' not in kw:
            self.declarative_count = self.counter.next()
        self.__initargs__(kw)

    def __initargs__(self, new_attrs):
        pass

    def __call__(self, *args, **kw):
        current = self.__dict__.copy()
        current.update(kw)
        return self.__class__(*args, **current)

    @classmethod
    def singleton(cls):
        name = '_%s__singleton' % cls.__name__
        if not hasattr(cls, name):
            try:
                setattr(cls, name, cls(
                    declarative_count=cls.declarative_count))
            except TypeError:  # takes arguments
                setattr(cls, name, cls)
        return getattr(cls, name)

    def __sourcerepr__(self, source, binding=None):
        if binding and len(self.__dict__) > 3:
            return self._source_repr_class(source, binding=binding)
        vals = self.__dict__.copy()
        if 'declarative_count' in vals:
            del vals['declarative_count']
        args = []
        if (self.__unpackargs__ and self.__unpackargs__[0] == '*'
                and self.__unpackargs__[1] in vals):
            v = vals[self.__unpackargs__[1]]
            if isinstance(v, (list, int)):
                args.extend(map(source.makeRepr, v))
                del v[self.__unpackargs__[1]]
        for name in self.__unpackargs__:
            if name in vals:
                args.append(source.makeRepr(vals[name]))
                del vals[name]
            else:
                break
        args.extend('%s=%s' % (name, source.makeRepr(value))
                     for (name, value) in vals.iteritems())
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(args))

    def _source_repr_class(self, source, binding=None):
        d = self.__dict__.copy()
        if 'declarative_count' in d:
            del d['declarative_count']
        return source.makeClass(self, binding, d,
                                (self.__class__,))

    @classmethod
    def __classsourcerepr__(cls, source, binding=None):
        d = cls.__dict__.copy()
        del d['declarative_count']
        return source.makeClass(cls, binding or cls.__name__, d,
                                cls.__bases__)

    @classinstancemethod
    def __repr__(self, cls):
        if self:
            name = '%s object' % self.__class__.__name__
            v = self.__dict__.copy()
        else:
            name = '%s class' % cls.__name__
            v = cls.__dict__.copy()
        if 'declarative_count' in v:
            name = '%s %i' % (name, v.pop('declarative_count'))
        names = sorted(v)
        args = ['%s=self' % n if v[n] is self else '%s=%r' % (n, v[n])
            for n in self._repr_vars(names)]
        if not args:
            return '<%s>' % name
        return '<%s %s>' % (name, ' '.join(args))

    @staticmethod
    def _repr_vars(dictNames):
        return sorted(n for n in dictNames
            if not n.startswith('_') and n != 'declarative_count')
