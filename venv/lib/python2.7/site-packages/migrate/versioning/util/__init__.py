#!/usr/bin/env python
# -*- coding: utf-8 -*-
""".. currentmodule:: migrate.versioning.util"""

import warnings
import logging
from decorator import decorator
from pkg_resources import EntryPoint

import six
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from migrate import exceptions
from migrate.versioning.util.keyedinstance import KeyedInstance
from migrate.versioning.util.importpath import import_path


log = logging.getLogger(__name__)

def load_model(dotted_name):
    """Import module and use module-level variable".

    :param dotted_name: path to model in form of string: ``some.python.module:Class``

    .. versionchanged:: 0.5.4

    """
    if isinstance(dotted_name, six.string_types):
        if ':' not in dotted_name:
            # backwards compatibility
            warnings.warn('model should be in form of module.model:User '
                'and not module.model.User', exceptions.MigrateDeprecationWarning)
            dotted_name = ':'.join(dotted_name.rsplit('.', 1))
        return EntryPoint.parse('x=%s' % dotted_name).load(False)
    else:
        # Assume it's already loaded.
        return dotted_name

def asbool(obj):
    """Do everything to use object as bool"""
    if isinstance(obj, six.string_types):
        obj = obj.strip().lower()
        if obj in ['true', 'yes', 'on', 'y', 't', '1']:
            return True
        elif obj in ['false', 'no', 'off', 'n', 'f', '0']:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    if obj in (True, False):
        return bool(obj)
    else:
        raise ValueError("String is not true/false: %r" % obj)

def guess_obj_type(obj):
    """Do everything to guess object type from string

    Tries to convert to `int`, `bool` and finally returns if not succeded.

    .. versionadded: 0.5.4
    """

    result = None

    try:
        result = int(obj)
    except:
        pass

    if result is None:
        try:
            result = asbool(obj)
        except:
            pass

    if result is not None:
        return result
    else:
        return obj

@decorator
def catch_known_errors(f, *a, **kw):
    """Decorator that catches known api errors

    .. versionadded: 0.5.4
    """

    try:
        return f(*a, **kw)
    except exceptions.PathFoundError as e:
        raise exceptions.KnownError("The path %s already exists" % e.args[0])

def construct_engine(engine, **opts):
    """.. versionadded:: 0.5.4

    Constructs and returns SQLAlchemy engine.

    Currently, there are 2 ways to pass create_engine options to :mod:`migrate.versioning.api` functions:

    :param engine: connection string or a existing engine
    :param engine_dict: python dictionary of options to pass to `create_engine`
    :param engine_arg_*: keyword parameters to pass to `create_engine` (evaluated with :func:`migrate.versioning.util.guess_obj_type`)
    :type engine_dict: dict
    :type engine: string or Engine instance
    :type engine_arg_*: string
    :returns: SQLAlchemy Engine

    .. note::

        keyword parameters override ``engine_dict`` values.

    """
    if isinstance(engine, Engine):
        return engine
    elif not isinstance(engine, six.string_types):
        raise ValueError("you need to pass either an existing engine or a database uri")

    # get options for create_engine
    if opts.get('engine_dict') and isinstance(opts['engine_dict'], dict):
        kwargs = opts['engine_dict']
    else:
        kwargs = dict()

    # DEPRECATED: handle echo the old way
    echo = asbool(opts.get('echo', False))
    if echo:
        warnings.warn('echo=True parameter is deprecated, pass '
            'engine_arg_echo=True or engine_dict={"echo": True}',
            exceptions.MigrateDeprecationWarning)
        kwargs['echo'] = echo

    # parse keyword arguments
    for key, value in six.iteritems(opts):
        if key.startswith('engine_arg_'):
            kwargs[key[11:]] = guess_obj_type(value)

    log.debug('Constructing engine')
    # TODO: return create_engine(engine, poolclass=StaticPool, **kwargs)
    # seems like 0.5.x branch does not work with engine.dispose and staticpool
    return create_engine(engine, **kwargs)

@decorator
def with_engine(f, *a, **kw):
    """Decorator for :mod:`migrate.versioning.api` functions
    to safely close resources after function usage.

    Passes engine parameters to :func:`construct_engine` and
    resulting parameter is available as kw['engine'].

    Engine is disposed after wrapped function is executed.

    .. versionadded: 0.6.0
    """
    url = a[0]
    engine = construct_engine(url, **kw)

    try:
        kw['engine'] = engine
        return f(*a, **kw)
    finally:
        if isinstance(engine, Engine) and engine is not url:
            log.debug('Disposing SQLAlchemy engine %s', engine)
            engine.dispose()


class Memoize(object):
    """Memoize(fn) - an instance which acts like fn but memoizes its arguments
       Will only work on functions with non-mutable arguments

       ActiveState Code 52201
    """
    def __init__(self, fn):
        self.fn = fn
        self.memo = {}

    def __call__(self, *args):
        if args not in self.memo:
            self.memo[args] = self.fn(*args)
        return self.memo[args]
