# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
'imports' a string -- converts a string to a Python object, importing
any necessary modules and evaluating the expression.  Everything
before the : in an import expression is the module path; everything
after is an expression to be evaluated in the namespace of that
module.

Alternately, if no : is present, then import the modules and get the
attributes as necessary.  Arbitrary expressions are not allowed in
that case.
"""

def eval_import(s):
    """
    Import a module, or import an object from a module.

    A module name like ``foo.bar:baz()`` can be used, where
    ``foo.bar`` is the module, and ``baz()`` is an expression
    evaluated in the context of that module.  Note this is not safe on
    arbitrary strings because of the eval.
    """
    if ':' not in s:
        return simple_import(s)
    module_name, expr = s.split(':', 1)
    module = import_module(module_name)
    obj = eval(expr, module.__dict__)
    return obj

def simple_import(s):
    """
    Import a module, or import an object from a module.

    A name like ``foo.bar.baz`` can be a module ``foo.bar.baz`` or a
    module ``foo.bar`` with an object ``baz`` in it, or a module
    ``foo`` with an object ``bar`` with an attribute ``baz``.
    """
    parts = s.split('.')
    module = import_module(parts[0])
    name = parts[0]
    parts = parts[1:]
    last_import_error = None
    while parts:
        name += '.' + parts[0]
        try:
            module = import_module(name)
            parts = parts[1:]
        except ImportError, e:
            last_import_error = e
            break
    obj = module
    while parts:
        try:
            obj = getattr(module, parts[0])
        except AttributeError:
            raise ImportError(
                "Cannot find %s in module %r (stopped importing modules with error %s)" % (parts[0], module, last_import_error))
        parts = parts[1:]
    return obj

def import_module(s):
    """
    Import a module.
    """
    mod = __import__(s)
    parts = s.split('.')
    for part in parts[1:]:
        mod = getattr(mod, part)
    return mod

def try_import_module(module_name):
    """
    Imports a module, but catches import errors.  Only catches errors
    when that module doesn't exist; if that module itself has an
    import error it will still get raised.  Returns None if the module
    doesn't exist.
    """
    try:
        return import_module(module_name)
    except ImportError, e:
        if not getattr(e, 'args', None):
            raise
        desc = e.args[0]
        if not desc.startswith('No module named '):
            raise
        desc = desc[len('No module named '):]
        # If you import foo.bar.baz, the bad import could be any
        # of foo.bar.baz, bar.baz, or baz; we'll test them all:
        parts = module_name.split('.')
        for i in range(len(parts)):
            if desc == '.'.join(parts[i:]):
                return None
        raise
