''' This module contains code that helps in maintaining the Ckan codebase. '''

import logging
import re

log = logging.getLogger(__name__)


def deprecated(message=''):
    ''' This is a decorator used to mark functions as deprecated.

    It logs a warning when the function is called. If a message is
    passed it is also logged, this can be useful to indicate for example
    that a different function should be used instead.

    Additionally an exception is raised if the functions docstring does
    not contain the word `deprecated`.'''
    def decorator(fn):
        # When decorating a function check that the docstring is correct.
        if not fn.__doc__ or not re.search(r'\bdeprecated\b',
                                           fn.__doc__, re.IGNORECASE):
            raise Exception('Function %s() in module %s has been deprecated '
                            'but this is not mentioned in the docstring. '
                            'Please update the docstring for the function. '
                            'It must include the word `deprecated`.'
                            % (fn.__name__, fn.__module__))
        # Log deprecated functions
        log.info('Function %s() in module %s has been deprecated. %s'
                            % (fn.__name__, fn.__module__, message))

        def wrapped(*args, **kw):
            log.warning('Function %s() in module %s has been deprecated '
                         'and will be removed in a later release of ckan. %s'
                         % (fn.__name__, fn.__module__, message))
            return fn(*args, **kw)
        return wrapped
    return decorator

def deprecate_context_item(item_name, message=''):
    ''' Deprecate a named item in the global context object.

    It logs a warning when the item is accessed.  If a mesage is passed, it is
    also logged.  This can be useful to indicate for example that a different
    function should be used instead.

    No warnings are given when an attempt to change or delete the named item
    from the context object.

    Example usage:

    >>> c.facets = "Foobar"
    >>> deprecate_context_item('facets', 'Use `c.search_facets` instead')
    >>> print c.facets
    2012-07-12 13:27:06,294 WARNI [ckan.lib.maintain] c.facets has been deprecated [...]
    Foobar

    This function works by attaching a property to the underlying
    `pylons.util.AttribSafeContextObj` object which provides the storage of the
    context object.  ie - it adds a class-level attribute to the
    `pylons.util.AttribSafeContextObj` at runtime.
    '''
    # prevent a circular import
    from ckan.lib.base import c


    # we need to store the origional __getattr__ and replace with our own one
    if not hasattr(c.__class__, '__old_getattr__'):
        def custom__getattr__(self, name):
            # get the origional __getattr__ so we can access things
            __old_getattr__ = self.__class__.__dict__['__old_getattr__']
            # see if we have a __depricated_properties__ for this name and
            # if so log a warning
            try:
                depricated = __old_getattr__(self, '__depricated_properties__')
                if name in depricated:
                    log.warn(depricated[name])
            except AttributeError:
                pass
            # return the requested value
            return __old_getattr__(self, name)

        # get store the old __getattr__ method and then replace it
        __old_getattr__ =  getattr(c.__class__, '__getattr__')
        setattr(c.__class__, '__old_getattr__', __old_getattr__)
        setattr(c.__class__, '__getattr__', custom__getattr__)

    # if c.__depricated_properties__ is not set it returns ''
    if not c.__depricated_properties__:
        c.__depricated_properties__ = {}
    c.__depricated_properties__[item_name] = message
