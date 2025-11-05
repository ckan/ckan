# encoding: utf-8

"""Flask blueprints for CKAN

This package contains Flask blueprints that replace the Pylons controllers.
Each blueprint maps to a corresponding Pylons controller for backward compatibility.
"""

__all__ = [
    'home',
    'package',
    'group',
    'organization',
    'user',
    'api',
    'admin',
    'feed',
    'tag',
]
