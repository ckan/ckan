"""
A dynamic-scope-like system, aka fluid variables.

The idea behind dynamic scoped variables is for when, at one level,
you want to change the behavior of something you call.  Except you
can't pass in any new arguments (e.g., there's some function or object
inbetween you and the thing you want to change), or you can't predict
exactly what you will want to change.

You should use it like::

    context = Context()

    def do_stuff():
        state = context.set(inside='do_stuff')
        try:
            do stuff...
        finally:
            state.restore()

Then ``context.inside`` will be set to ``'do_stuff'`` inside that try
block.  If a value isn't set, you'll get an attribute error.

Note that all values are thread local; this means you cannot use a
context object to pass information to another thread.  In a
single-thread environment it doesn't really matter.

Typically you will create ``Context`` instances for your application,
environment, etc.  These should be global module-level variables, that
may be imported by any interested module; each instance is a namespace
of its own.

Sometimes it's nice to have default values, instead of getting
attribute errors.  This makes it easier to put in new variables that
are intended to be used elsewhere, without having to use
``getattr(context, 'var', default)`` to avoid AttributeErrors.
There are two ways (that can be used together) to do this.

First, when instantiating a ``Context`` object, you can give it a
``default`` value.  If given, then all variables will default to that
value.  ``None`` is a typical value for that.

Another is ``context.set_default(**vars)``, which will set only those
variables to default values.  This will not effect the stack of
scopes, but will only add defaults.

When Python 2.5 comes out, this syntax would certainly be useful::

    with context(page='view'):
        do stuff...

And ``page`` will be set to ``'view'`` only inside that ``with`` block.
"""

import threading

from itertools import count

__all__ = ['Context', 'ContextRestoreError']

_restore_ids = count()


class NoDefault(object):
    """A dummy value used for parameters with no default."""


class ContextRestoreError(Exception):
    """Raised when something is restored out-of-order."""


class Context(object):

    def __init__(self, default=NoDefault):
        self.__dict__['_local'] = threading.local()
        self.__dict__['_default'] = default

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError
        try:
            stack = self._local.stack
        except AttributeError:
            stack = []
        for i in range(len(stack) - 1, -1, -1):
            if attr in stack[i][0]:
                return stack[i][0][attr]
        if self._default is NoDefault:
            raise AttributeError(
                "The attribute %s has not been set on %r"
                % (attr, self))
        return self._default

    def __setattr__(self, attr, value):
        raise AttributeError(
            "You can only write attribute on context object with the .set() method")

    def set(self, **kw):
        state_id = _restore_ids.next()
        try:
            stack = self._local.stack
        except AttributeError:
            stack = self._local.stack = [({}, -1)]
        restorer = RestoreState(self, state_id)
        stack.append((kw, state_id))
        return restorer

    def _restore(self, state_id):
        try:
            stack = self._local.stack
        except AttributeError:
            raise ContextRestoreError(
                "Tried to restore context %r (to state ID %s) but no variables have been set in context"
                % (self, state_id))
        if stack[-1][1] == -1:
            raise ContextRestoreError(
                "Out of order restoration of context %r (to state ID %s); the stack state is empty"
                % (self, state_id))
        if stack[-1][1] != state_id:
            raise ContextRestoreError(
                "Out of order restoration of context %r (to state ID %s) when last state is %s"
                % (self, state_id, stack[-1][1]))
        stack.pop()

    def set_default(self, **kw):
        try:
            stack = self._local.stack
        except AttributeError:
            stack = self._local.stack = [({}, -1)]
        stack[0][0].update(kw)

    def __repr__(self):
        try:
            stack = self._local.stack
        except AttributeError:
            stack = []
        myid = hex(abs(id(self)))[2:]
        if not stack:
            return '<%s %s (empty)>' % (self.__class__.__name__, myid)
        cur = {}
        for kw, _state_id in stack:
            cur.update(kw)
        keys = sorted(cur)
        varlist = []
        for key in keys:
            rep = repr(cur[key])
            if len(rep) > 10:
                rep = rep[:9] + '...' + rep[-1]
            varlist.append('%s=%s' % (key, rep))
        return '<%s %s %s>' % (
            self.__class__.__name__, myid, ' '.join(varlist))


class RestoreState(object):

    def __init__(self, context, state_id):
        self.state_id = state_id
        self.context = context
        self.restored = False

    def restore(self):
        if self.restored:
            # @@: Should this really be allowed?
            return
        self.context._restore(self.state_id)
        self.restored = True
