"""Deprecated: The decorator module is no longer packaged with Pylons as
pylons.decorator, use the decorator module instead.
"""
import warnings

from pylons.decorators._decorator import *

warnings.warn('The decorator module is no longer packaged with Pylons as '
              'pylons.decorator, use the decorator module instead.',
              DeprecationWarning, 2)
