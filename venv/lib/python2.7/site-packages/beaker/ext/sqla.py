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


class SqlaNamespaceManager(OpenResourceNamespaceManager):
    binds = SyncDict()
    tables = SyncDict()

    @classmethod
    def _init_dependencies(cls):
        global sa
        if sa is not None:
            return
        try:
            import sqlalchemy as sa
        except ImportError:
            raise InvalidCacheBackendError("SQLAlchemy, which is required by "
                                            "this backend, is not installed")

    def __init__(self, namespace, bind, table, data_dir=None, lock_dir=None,
                 **kwargs):
        """Create a namespace manager for use with a database table via
        SQLAlchemy.

        ``bind``
            SQLAlchemy ``Engine`` or ``Connection`` object

        ``table``
            SQLAlchemy ``Table`` object in which to store namespace data.
            This should usually be something created by ``make_cache_table``.
        """
        OpenResourceNamespaceManager.__init__(self, namespace)

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_db_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        self.bind = self.__class__.binds.get(str(bind.url), lambda: bind)
        self.table = self.__class__.tables.get('%s:%s' % (bind.url, table.name),
                                               lambda: table)
        self.hash = {}
        self._is_new = False
        self.loaded = False

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="databasecontainer/funclock/%s" % self.namespace,
            lock_dir=self.lock_dir)

    def do_open(self, flags, replace):
        if self.loaded:
            self.flags = flags
            return
        select = sa.select([self.table.c.data],
                           (self.table.c.namespace == self.namespace))
        result = self.bind.execute(select).fetchone()
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
            if self._is_new:
                insert = self.table.insert()
                self.bind.execute(insert, namespace=self.namespace, data=self.hash,
                                  accessed=datetime.now(), created=datetime.now())
                self._is_new = False
            else:
                update = self.table.update(self.table.c.namespace == self.namespace)
                self.bind.execute(update, data=self.hash, accessed=datetime.now())
        self.flags = None

    def do_remove(self):
        delete = self.table.delete(self.table.c.namespace == self.namespace)
        self.bind.execute(delete)
        self.hash = {}
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


class SqlaContainer(Container):
    namespace_manager = SqlaNamespaceManager


def make_cache_table(metadata, table_name='beaker_cache', schema_name=None):
    """Return a ``Table`` object suitable for storing cached values for the
    namespace manager.  Do not create the table."""
    return sa.Table(table_name, metadata,
                    sa.Column('namespace', sa.String(255), primary_key=True),
                    sa.Column('accessed', sa.DateTime, nullable=False),
                    sa.Column('created', sa.DateTime, nullable=False),
                    sa.Column('data', sa.PickleType, nullable=False),
                    schema=schema_name if schema_name else metadata.schema)
