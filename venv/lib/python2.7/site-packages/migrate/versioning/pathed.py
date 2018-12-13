"""
   A path/directory class.
"""

import os
import shutil
import logging

from migrate import exceptions
from migrate.versioning.config import *
from migrate.versioning.util import KeyedInstance


log = logging.getLogger(__name__)

class Pathed(KeyedInstance):
    """
    A class associated with a path/directory tree.

    Only one instance of this class may exist for a particular file;
    __new__ will return an existing instance if possible
    """
    parent = None

    @classmethod
    def _key(cls, path):
        return str(path)

    def __init__(self, path):
        self.path = path
        if self.__class__.parent is not None:
            self._init_parent(path)

    def _init_parent(self, path):
        """Try to initialize this object's parent, if it has one"""
        parent_path = self.__class__._parent_path(path)
        self.parent = self.__class__.parent(parent_path)
        log.debug("Getting parent %r:%r" % (self.__class__.parent, parent_path))
        self.parent._init_child(path, self)

    def _init_child(self, child, path):
        """Run when a child of this object is initialized.

        Parameters: the child object; the path to this object (its
        parent)
        """

    @classmethod
    def _parent_path(cls, path):
        """
        Fetch the path of this object's parent from this object's path.
        """
        # os.path.dirname(), but strip directories like files (like
        # unix basename)
        #
        # Treat directories like files...
        if path[-1] == '/':
            path = path[:-1]
        ret = os.path.dirname(path)
        return ret

    @classmethod
    def require_notfound(cls, path):
        """Ensures a given path does not already exist"""
        if os.path.exists(path):
            raise exceptions.PathFoundError(path)

    @classmethod
    def require_found(cls, path):
        """Ensures a given path already exists"""
        if not os.path.exists(path):
            raise exceptions.PathNotFoundError(path)

    def __str__(self):
        return self.path
