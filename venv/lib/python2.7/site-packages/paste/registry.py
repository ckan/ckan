# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Registry for handling request-local module globals sanely

Dealing with module globals in a thread-safe way is good if your
application is the sole responder in a thread, however that approach fails
to properly account for various scenarios that occur with WSGI applications
and middleware.

What is actually needed in the case where a module global is desired that
is always set properly depending on the current request, is a stacked
thread-local object. Such an object is popped or pushed during the request
cycle so that it properly represents the object that should be active for
the current request.

To make it easy to deal with such variables, this module provides a special
StackedObjectProxy class which you can instantiate and attach to your
module where you'd like others to access it. The object you'd like this to
actually "be" during the request is then registered with the
RegistryManager middleware, which ensures that for the scope of the current
WSGI application everything will work properly.

Example:

.. code-block:: python

    #yourpackage/__init__.py

    from paste.registry import RegistryManager, StackedObjectProxy
    myglobal = StackedObjectProxy()

    #wsgi app stack
    app = RegistryManager(yourapp)

    #inside your wsgi app
    class yourapp(object):
        def __call__(self, environ, start_response):
            obj = someobject  # The request-local object you want to access
                              # via yourpackage.myglobal
            if environ.has_key('paste.registry'):
                environ['paste.registry'].register(myglobal, obj)

You will then be able to import yourpackage anywhere in your WSGI app or in
the calling stack below it and be assured that it is using the object you
registered with Registry.

RegistryManager can be in the WSGI stack multiple times, each time it
appears it registers a new request context.


Performance
===========

The overhead of the proxy object is very minimal, however if you are using
proxy objects extensively (Thousands of accesses per request or more), there
are some ways to avoid them. A proxy object runs approximately 3-20x slower
than direct access to the object, this is rarely your performance bottleneck
when developing web applications.

Should you be developing a system which may be accessing the proxy object
thousands of times per request, the performance of the proxy will start to
become more noticeable. In that circumstance, the problem can be avoided by
getting at the actual object via the proxy with the ``_current_obj`` function:

.. code-block:: python

    #sessions.py
    Session = StackedObjectProxy()
    # ... initialization code, etc.

    # somemodule.py
    import sessions

    def somefunc():
        session = sessions.Session._current_obj()
        # ... tons of session access

This way the proxy is used only once to retrieve the object for the current
context and the overhead is minimized while still making it easy to access
the underlying object. The ``_current_obj`` function is preceded by an
underscore to more likely avoid clashing with the contained object's
attributes.

**NOTE:** This is *highly* unlikely to be an issue in the vast majority of
cases, and requires incredibly large amounts of proxy object access before
one should consider the proxy object to be causing slow-downs. This section
is provided solely in the extremely rare case that it is an issue so that a
quick way to work around it is documented.

"""
import sys
import paste.util.threadinglocal as threadinglocal

__all__ = ['StackedObjectProxy', 'RegistryManager', 'StackedObjectRestorer',
           'restorer']

class NoDefault(object): pass

class StackedObjectProxy(object):
    """Track an object instance internally using a stack

    The StackedObjectProxy proxies access to an object internally using a
    stacked thread-local. This makes it safe for complex WSGI environments
    where access to the object may be desired in multiple places without
    having to pass the actual object around.

    New objects are added to the top of the stack with _push_object while
    objects can be removed with _pop_object.

    """
    def __init__(self, default=NoDefault, name="Default"):
        """Create a new StackedObjectProxy

        If a default is given, its used in every thread if no other object
        has been pushed on.

        """
        self.__dict__['____name__'] = name
        self.__dict__['____local__'] = threadinglocal.local()
        if default is not NoDefault:
            self.__dict__['____default_object__'] = default

    def __dir__(self):
        """Return a list of the StackedObjectProxy's and proxied
        object's (if one exists) names.
        """
        dir_list = dir(self.__class__) + self.__dict__.keys()
        try:
            dir_list.extend(dir(self._current_obj()))
        except TypeError:
            pass
        dir_list.sort()
        return dir_list

    def __getattr__(self, attr):
        return getattr(self._current_obj(), attr)

    def __setattr__(self, attr, value):
        setattr(self._current_obj(), attr, value)

    def __delattr__(self, name):
        delattr(self._current_obj(), name)

    def __getitem__(self, key):
        return self._current_obj()[key]

    def __setitem__(self, key, value):
        self._current_obj()[key] = value

    def __delitem__(self, key):
        del self._current_obj()[key]

    def __call__(self, *args, **kw):
        return self._current_obj()(*args, **kw)

    def __repr__(self):
        try:
            return repr(self._current_obj())
        except (TypeError, AttributeError):
            return '<%s.%s object at 0x%x>' % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self))

    def __iter__(self):
        return iter(self._current_obj())

    def __len__(self):
        return len(self._current_obj())

    def __contains__(self, key):
        return key in self._current_obj()

    def __nonzero__(self):
        return bool(self._current_obj())

    def _current_obj(self):
        """Returns the current active object being proxied to

        In the event that no object was pushed, the default object if
        provided will be used. Otherwise, a TypeError will be raised.

        """
        try:
            objects = self.____local__.objects
        except AttributeError:
            objects = None
        if objects:
            return objects[-1]
        else:
            obj = self.__dict__.get('____default_object__', NoDefault)
            if obj is not NoDefault:
                return obj
            else:
                raise TypeError(
                    'No object (name: %s) has been registered for this '
                    'thread' % self.____name__)

    def _push_object(self, obj):
        """Make ``obj`` the active object for this thread-local.

        This should be used like:

        .. code-block:: python

            obj = yourobject()
            module.glob = StackedObjectProxy()
            module.glob._push_object(obj)
            try:
                ... do stuff ...
            finally:
                module.glob._pop_object(conf)

        """
        try:
            self.____local__.objects.append(obj)
        except AttributeError:
            self.____local__.objects = []
            self.____local__.objects.append(obj)

    def _pop_object(self, obj=None):
        """Remove a thread-local object.

        If ``obj`` is given, it is checked against the popped object and an
        error is emitted if they don't match.

        """
        try:
            popped = self.____local__.objects.pop()
            if obj and popped is not obj:
                raise AssertionError(
                    'The object popped (%s) is not the same as the object '
                    'expected (%s)' % (popped, obj))
        except AttributeError:
            raise AssertionError('No object has been registered for this thread')

    def _object_stack(self):
        """Returns all of the objects stacked in this container

        (Might return [] if there are none)
        """
        try:
            try:
                objs = self.____local__.objects
            except AttributeError:
                return []
            return objs[:]
        except AssertionError:
            return []

    # The following methods will be swapped for their original versions by
    # StackedObjectRestorer when restoration is enabled. The original
    # functions (e.g. _current_obj) will be available at _current_obj_orig

    def _current_obj_restoration(self):
        request_id = restorer.in_restoration()
        if request_id:
            return restorer.get_saved_proxied_obj(self, request_id)
        return self._current_obj_orig()
    _current_obj_restoration.__doc__ = \
        ('%s\n(StackedObjectRestorer restoration enabled)' % \
         _current_obj.__doc__)

    def _push_object_restoration(self, obj):
        if not restorer.in_restoration():
            self._push_object_orig(obj)
    _push_object_restoration.__doc__ = \
        ('%s\n(StackedObjectRestorer restoration enabled)' % \
         _push_object.__doc__)

    def _pop_object_restoration(self, obj=None):
        if not restorer.in_restoration():
            self._pop_object_orig(obj)
    _pop_object_restoration.__doc__ = \
        ('%s\n(StackedObjectRestorer restoration enabled)' % \
         _pop_object.__doc__)

class Registry(object):
    """Track objects and stacked object proxies for removal

    The Registry object is instantiated a single time for the request no
    matter how many times the RegistryManager is used in a WSGI stack. Each
    RegistryManager must call ``prepare`` before continuing the call to
    start a new context for object registering.

    Each context is tracked with a dict inside a list. The last list
    element is the currently executing context. Each context dict is keyed
    by the id of the StackedObjectProxy instance being proxied, the value
    is a tuple of the StackedObjectProxy instance and the object being
    tracked.

    """
    def __init__(self):
        """Create a new Registry object

        ``prepare`` must still be called before this Registry object can be
        used to register objects.

        """
        self.reglist = []

    def prepare(self):
        """Used to create a new registry context

        Anytime a new RegistryManager is called, ``prepare`` needs to be
        called on the existing Registry object. This sets up a new context
        for registering objects.

        """
        self.reglist.append({})

    def register(self, stacked, obj):
        """Register an object with a StackedObjectProxy"""
        myreglist = self.reglist[-1]
        stacked_id = id(stacked)
        if stacked_id in myreglist:
            stacked._pop_object(myreglist[stacked_id][1])
            del myreglist[stacked_id]
        stacked._push_object(obj)
        myreglist[stacked_id] = (stacked, obj)

    def multiregister(self, stacklist):
        """Register a list of tuples

        Similar call semantics as register, except this registers
        multiple objects at once.

        Example::

            registry.multiregister([(sop, obj), (anothersop, anotherobj)])

        """
        myreglist = self.reglist[-1]
        for stacked, obj in stacklist:
            stacked_id = id(stacked)
            if stacked_id in myreglist:
                stacked._pop_object(myreglist[stacked_id][1])
                del myreglist[stacked_id]
            stacked._push_object(obj)
            myreglist[stacked_id] = (stacked, obj)

    # Replace now does the same thing as register
    replace = register

    def cleanup(self):
        """Remove all objects from all StackedObjectProxy instances that
        were tracked at this Registry context"""
        for stacked, obj in self.reglist[-1].itervalues():
            stacked._pop_object(obj)
        self.reglist.pop()

class RegistryManager(object):
    """Creates and maintains a Registry context

    RegistryManager creates a new registry context for the registration of
    StackedObjectProxy instances. Multiple RegistryManager's can be in a
    WSGI stack and will manage the context so that the StackedObjectProxies
    always proxy to the proper object.

    The object being registered can be any object sub-class, list, or dict.

    Registering objects is done inside a WSGI application under the
    RegistryManager instance, using the ``environ['paste.registry']``
    object which is a Registry instance.

    """
    def __init__(self, application, streaming=False):
        self.application = application
        self.streaming = streaming

    def __call__(self, environ, start_response):
        app_iter = None
        reg = environ.setdefault('paste.registry', Registry())
        reg.prepare()
        if self.streaming:
            return self.streaming_iter(reg, environ, start_response)

        try:
            app_iter = self.application(environ, start_response)
        except Exception, e:
            # Regardless of if the content is an iterable, generator, list
            # or tuple, we clean-up right now. If its an iterable/generator
            # care should be used to ensure the generator has its own ref
            # to the actual object
            if environ.get('paste.evalexception'):
                # EvalException is present in the WSGI stack
                expected = False
                for expect in environ.get('paste.expected_exceptions', []):
                    if isinstance(e, expect):
                        expected = True
                if not expected:
                    # An unexpected exception: save state for EvalException
                    restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        except:
            # Save state for EvalException if it's present
            if environ.get('paste.evalexception'):
                restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        else:
            reg.cleanup()

        return app_iter

    def streaming_iter(self, reg, environ, start_response):
        try:
            for item in self.application(environ, start_response):
                yield item
        except Exception, e:
            # Regardless of if the content is an iterable, generator, list
            # or tuple, we clean-up right now. If its an iterable/generator
            # care should be used to ensure the generator has its own ref
            # to the actual object
            if environ.get('paste.evalexception'):
                # EvalException is present in the WSGI stack
                expected = False
                for expect in environ.get('paste.expected_exceptions', []):
                    if isinstance(e, expect):
                        expected = True
                if not expected:
                    # An unexpected exception: save state for EvalException
                    restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        except:
            # Save state for EvalException if it's present
            if environ.get('paste.evalexception'):
                restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        else:
            reg.cleanup()


class StackedObjectRestorer(object):
    """Track StackedObjectProxies and their proxied objects for automatic
    restoration within EvalException's interactive debugger.

    An instance of this class tracks all StackedObjectProxy state in existence
    when unexpected exceptions are raised by WSGI applications housed by
    EvalException and RegistryManager. Like EvalException, this information is
    stored for the life of the process.

    When an unexpected exception occurs and EvalException is present in the
    WSGI stack, save_registry_state is intended to be called to store the
    Registry state and enable automatic restoration on all currently registered
    StackedObjectProxies.

    With restoration enabled, those StackedObjectProxies' _current_obj
    (overwritten by _current_obj_restoration) method's strategy is modified:
    it will return its appropriate proxied object from the restorer when
    a restoration context is active in the current thread.

    The StackedObjectProxies' _push/pop_object methods strategies are also
    changed: they no-op when a restoration context is active in the current
    thread (because the pushing/popping work is all handled by the
    Registry/restorer).

    The request's Registry objects' reglists are restored from the restorer
    when a restoration context begins, enabling the Registry methods to work
    while their changes are tracked by the restorer.

    The overhead of enabling restoration is negligible (another threadlocal
    access for the changed StackedObjectProxy methods) for normal use outside
    of a restoration context, but worth mentioning when combined with
    StackedObjectProxies normal overhead. Once enabled it does not turn off,
    however:

    o Enabling restoration only occurs after an unexpected exception is
    detected. The server is likely to be restarted shortly after the exception
    is raised to fix the cause

    o StackedObjectRestorer is only enabled when EvalException is enabled (not
    on a production server) and RegistryManager exists in the middleware
    stack"""
    def __init__(self):
        # Registries and their saved reglists by request_id
        self.saved_registry_states = {}
        self.restoration_context_id = threadinglocal.local()

    def save_registry_state(self, environ):
        """Save the state of this request's Registry (if it hasn't already been
        saved) to the saved_registry_states dict, keyed by the request's unique
        identifier"""
        registry = environ.get('paste.registry')
        if not registry or not len(registry.reglist) or \
                self.get_request_id(environ) in self.saved_registry_states:
            # No Registry, no state to save, or this request's state has
            # already been saved
            return

        self.saved_registry_states[self.get_request_id(environ)] = \
            (registry, registry.reglist[:])

        # Tweak the StackedObjectProxies we want to save state for -- change
        # their methods to act differently when a restoration context is active
        # in the current thread
        for reglist in registry.reglist:
            for stacked, obj in reglist.itervalues():
                self.enable_restoration(stacked)

    def get_saved_proxied_obj(self, stacked, request_id):
        """Retrieve the saved object proxied by the specified
        StackedObjectProxy for the request identified by request_id"""
        # All state for the request identified by request_id
        reglist = self.saved_registry_states[request_id][1]

        # The top of the stack was current when the exception occurred
        stack_level = len(reglist) - 1
        stacked_id = id(stacked)
        while True:
            if stack_level < 0:
                # Nothing registered: Call _current_obj_orig to raise a
                # TypeError
                return stacked._current_obj_orig()
            context = reglist[stack_level]
            if stacked_id in context:
                break
            # This StackedObjectProxy may not have been registered by the
            # RegistryManager that was active when the exception was raised --
            # continue searching down the stack until it's found
            stack_level -= 1
        return context[stacked_id][1]

    def enable_restoration(self, stacked):
        """Replace the specified StackedObjectProxy's methods with their
        respective restoration versions.

        _current_obj_restoration forces recovery of the saved proxied object
        when a restoration context is active in the current thread.

        _push/pop_object_restoration avoid pushing/popping data
        (pushing/popping is only done at the Registry level) when a restoration
        context is active in the current thread"""
        if '_current_obj_orig' in stacked.__dict__:
            # Restoration already enabled
            return

        for func_name in ('_current_obj', '_push_object', '_pop_object'):
            orig_func = getattr(stacked, func_name)
            restoration_func = getattr(stacked, func_name + '_restoration')
            stacked.__dict__[func_name + '_orig'] = orig_func
            stacked.__dict__[func_name] = restoration_func

    def get_request_id(self, environ):
        """Return a unique identifier for the current request"""
        from paste.evalexception.middleware import get_debug_count
        return get_debug_count(environ)

    def restoration_begin(self, request_id):
        """Enable a restoration context in the current thread for the specified
        request_id"""
        if request_id in self.saved_registry_states:
            # Restore the old Registry object's state
            registry, reglist = self.saved_registry_states[request_id]
            registry.reglist = reglist

        self.restoration_context_id.request_id = request_id

    def restoration_end(self):
        """Register a restoration context as finished, if one exists"""
        try:
            del self.restoration_context_id.request_id
        except AttributeError:
            pass

    def in_restoration(self):
        """Determine if a restoration context is active for the current thread.
        Returns the request_id it's active for if so, otherwise False"""
        return getattr(self.restoration_context_id, 'request_id', False)

restorer = StackedObjectRestorer()


# Paste Deploy entry point
def make_registry_manager(app, global_conf):
    return RegistryManager(app)

make_registry_manager.__doc__ = RegistryManager.__doc__
