from beaker._compat import pickle

import logging
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError
from beaker.synchronization import null_synchronizer

log = logging.getLogger(__name__)

db = None


class GoogleNamespaceManager(OpenResourceNamespaceManager):
    tables = {}

    @classmethod
    def _init_dependencies(cls):
        global db
        if db is not None:
            return
        try:
            db = __import__('google.appengine.ext.db').appengine.ext.db
        except ImportError:
            raise InvalidCacheBackendError("Datastore cache backend requires the "
                                           "'google.appengine.ext' library")

    def __init__(self, namespace, table_name='beaker_cache', **params):
        """Creates a datastore namespace manager"""
        OpenResourceNamespaceManager.__init__(self, namespace)

        def make_cache():
            table_dict = dict(created=db.DateTimeProperty(),
                              accessed=db.DateTimeProperty(),
                              data=db.BlobProperty())
            table = type(table_name, (db.Model,), table_dict)
            return table
        self.table_name = table_name
        self.cache = GoogleNamespaceManager.tables.setdefault(table_name, make_cache())
        self.hash = {}
        self._is_new = False
        self.loaded = False
        self.log_debug = logging.DEBUG >= log.getEffectiveLevel()

        # Google wants namespaces to start with letters, change the namespace
        # to start with a letter
        self.namespace = 'p%s' % self.namespace

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        # this is weird, should probably be present
        return null_synchronizer()

    def do_open(self, flags, replace):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return

        item = self.cache.get_by_key_name(self.namespace)

        if not item:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = pickle.loads(str(item.data))
            except (IOError, OSError, EOFError, pickle.PickleError):
                if self.log_debug:
                    log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            if self._is_new:
                item = self.cache(key_name=self.namespace)
                item.data = pickle.dumps(self.hash)
                item.created = datetime.now()
                item.accessed = datetime.now()
                item.put()
                self._is_new = False
            else:
                item = self.cache.get_by_key_name(self.namespace)
                item.data = pickle.dumps(self.hash)
                item.accessed = datetime.now()
                item.put()
        self.flags = None

    def do_remove(self):
        item = self.cache.get_by_key_name(self.namespace)
        item.delete()
        self.hash = {}

        # We can retain the fact that we did a load attempt, but since the
        # file is gone this will be a new namespace should it be saved.
        self._is_new = True

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return key in self.hash

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class GoogleContainer(Container):
    namespace_class = GoogleNamespaceManager
