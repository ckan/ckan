#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import sys

from pkg_resources import resource_filename

from migrate.versioning.config import *
from migrate.versioning import pathed


class Collection(pathed.Pathed):
    """A collection of templates of a specific type"""
    _mask = None

    def get_path(self, file):
        return os.path.join(self.path, str(file))


class RepositoryCollection(Collection):
    _mask = '%s'

class ScriptCollection(Collection):
    _mask = '%s.py_tmpl'

class ManageCollection(Collection):
    _mask = '%s.py_tmpl'

class SQLScriptCollection(Collection):
    _mask = '%s.py_tmpl'

class Template(pathed.Pathed):
    """Finds the paths/packages of various Migrate templates.

    :param path: Templates are loaded from migrate package
    if `path` is not provided.
    """
    pkg = 'migrate.versioning.templates'

    def __new__(cls, path=None):
        if path is None:
            path = cls._find_path(cls.pkg)
        return super(Template, cls).__new__(cls, path)

    def __init__(self, path=None):
        if path is None:
            path = Template._find_path(self.pkg)
        super(Template, self).__init__(path)
        self.repository = RepositoryCollection(os.path.join(path, 'repository'))
        self.script = ScriptCollection(os.path.join(path, 'script'))
        self.manage = ManageCollection(os.path.join(path, 'manage'))
        self.sql_script = SQLScriptCollection(os.path.join(path, 'sql_script'))

    @classmethod
    def _find_path(cls, pkg):
        """Returns absolute path to dotted python package."""
        tmp_pkg = pkg.rsplit('.', 1)

        if len(tmp_pkg) != 1:
            return resource_filename(tmp_pkg[0], tmp_pkg[1])
        else:
            return resource_filename(tmp_pkg[0], '')

    def _get_item(self, collection, theme=None):
        """Locates and returns collection.

        :param collection: name of collection to locate
        :param type_: type of subfolder in collection (defaults to "_default")
        :returns: (package, source)
        :rtype: str, str
        """
        item = getattr(self, collection)
        theme_mask = getattr(item, '_mask')
        theme = theme_mask % (theme or 'default')
        return item.get_path(theme)

    def get_repository(self, *a, **kw):
        """Calls self._get_item('repository', *a, **kw)"""
        return self._get_item('repository', *a, **kw)

    def get_script(self, *a, **kw):
        """Calls self._get_item('script', *a, **kw)"""
        return self._get_item('script', *a, **kw)

    def get_sql_script(self, *a, **kw):
        """Calls self._get_item('sql_script', *a, **kw)"""
        return self._get_item('sql_script', *a, **kw)

    def get_manage(self, *a, **kw):
        """Calls self._get_item('manage', *a, **kw)"""
        return self._get_item('manage', *a, **kw)
