"""Helpers for the `Pylons <http://pylonshq.com>`_ web framework

These helpers depend on Pylons' ``request``, ``response``, ``session``
objects or some other aspect of Pylons.  Most of them can be easily ported to
another framework by changing the API calls.
"""

# Do not import Pylons at module level; only within functions.  All WebHelpers
# modules should be importable on any Python system for the standard
# regression tests.

# Backward compatibility
from webhelpers.pylonslib.flash import *
