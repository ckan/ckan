from beaker._compat import pickle

import logging
import pickle
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict

log = logging.getLogger(__name__)

sa = None
pool = None
types = None


class DatabaseNamespaceManager(OpenResourceNamespaceManager):
    metadatas = SyncDict()
    tables = SyncDict()

    @classmethod
    def _init_dependencies(cls):
        global sa, pool, types
        if sa is not None:
            return
        try:
            import sqlalchemy as sa
            import sqlalchemy.pool as pool
            from sqlalchemy import types
        except ImportError:
            raise InvalidCacheBackendError("Database cache backend requires "
                                            "the 'sqlalchemy' library")

    def __init__(self, namespace, url=None, sa_opts=None, optimistic=False,
                 table_name='beaker_cache', data_dir=None, lock_dir=None,
                 schema_name=None, **params):
        """Creates a database namespace manager

        ``url``
            SQLAlchemy compliant db url
        ``sa_opts``
            A dictionary of SQLAlchemy keyword options to initialize the engine
            with.
        ``optimistic``
            Use optimistic session locking, note that this will result in an
            additional select when updating a cache value to compare version
            numbers.
        ``table_name``
            The table name to use in the database for the cache.
        ``schema_name``
            The schema name to use in the database for the cache.
        """
        OpenResourceNamespaceManager.__init__(self, namespace)

        if sa_opts is None:
            sa_opts = {}

        self.lock_dir = None

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_db_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        # Check to see if the table's been created before
        url = url or sa_opts['sa.url']
        table_key = url + table_name

        def make_cache():
            # Check to see if we have a connection pool open already
            meta_key = url + table_name

            def make_meta():
                # SQLAlchemy pops the url, this ensures it sticks around
                # later
                sa_opts['sa.url'] = url
                engine = sa.engine_from_config(sa_opts, 'sa.')
                meta = sa.MetaData()
                meta.bind = engine
                return meta
            meta = DatabaseNamespaceManager.metadatas.get(meta_key, make_meta)
            # Create the table object and cache it now
            cache = sa.Table(table_name, meta,
                             sa.Column('id', types.Integer, primary_key=True),
                             sa.Column('namespace', types.String(255), nullable=False),
                             sa.Column('accessed', types.DateTime, nullable=False),
                             sa.Column('created', types.DateTime, nullable=False),
                             sa.Column('data', types.PickleType, nullable=False),
                             sa.UniqueConstraint('namespace'),
                             schema=schema_name if schema_name else meta.schema
            )
            cache.create(checkfirst=True)
            return cache
        self.hash = {}
        self._is_new = False
        self.loaded = False
        self.cache = DatabaseNamespaceManager.tables.get(table_key, make_cache)

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="databasecontainer/funclock/%s/%s" % (
                self.namespace, key
            ),
            lock_dir=self.lock_dir)

    def do_open(self, flags, replace):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return

        cache = self.cache
        result_proxy = sa.select([cache.c.data],
                           cache.c.namespace == self.namespace
                          ).execute()
        result = result_proxy.fetchone()
        result_proxy.close()
        
        if not result:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = result['data']
            except (IOError, OSError, EOFError, pickle.PickleError,
                    pickle.PickleError):
                log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            cache = self.cache
            if self._is_new:
                cache.insert().execute(namespace=self.namespace, data=self.hash,
                                       accessed=datetime.now(),
                                       created=datetime.now())
                self._is_new = False
            else:
                cache.update(cache.c.namespace == self.namespace).execute(
                    data=self.hash, accessed=datetime.now())
        self.flags = None

    def do_remove(self):
        cache = self.cache
        cache.delete(cache.c.namespace == self.namespace).execute()
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


class DatabaseContainer(Container):
    namespace_manager = DatabaseNamespaceManager
