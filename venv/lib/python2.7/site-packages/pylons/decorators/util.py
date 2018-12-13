"""Decorator internal utilities"""
import pylons
from pylons.controllers import WSGIController

def get_pylons(decorator_args):
    """Return the `pylons` object: either the :mod`~pylons` module or
    the :attr:`~WSGIController._py_object` equivalent, searching a
    decorator's *args for the latter

    :attr:`~WSGIController._py_object` is more efficient as it provides
    direct access to the Pylons global variables.
    """
    if decorator_args:
        controller = decorator_args[0]
        if isinstance(controller, WSGIController):
            return controller._py_object
    return pylons
