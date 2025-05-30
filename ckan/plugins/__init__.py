# encoding: utf-8

from ckan.plugins.core import *  # noqa: F401, F403
from ckan.plugins.interfaces import *  # noqa: F401, F403


def __getattr__(name: str):
    if name == 'toolkit':
        import ckan.plugins.toolkit as t
        return t

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
