"""Container and Namespace classes"""
import errno

from ._compat import pickle, anydbm, add_metaclass, PYVER, unicode_text

import beaker.util as util
import logging
import os
import time

from beaker.exceptions import CreationAbortedError, MissingCacheParameter
from beaker.synchronization import _threading, file_synchronizer, \
     mutex_synchronizer, NameLock, null_synchronizer

__all__ = ['Value', 'Container', 'ContainerContext',
           'MemoryContainer', 'DBMContainer', 'NamespaceManager',
           'MemoryNamespaceManager', 'DBMNamespaceManager', 'FileContainer',
           'OpenResourceNamespaceManager',
           'FileNamespaceManager', 'CreationAbortedError']


logger = logging.getLogger('beaker.container')
if logger.isEnabledFor(logging.DEBUG):
    debug = logger.debug
else:
    def debug(message, *args):
        pass


class NamespaceManager(object):
    """Handles dictionary operations and locking for a namespace of
    values.

    :class:`.NamespaceManager` provides a dictionary-like interface,
    implementing ``__getitem__()``, ``__setitem__()``, and
    ``__contains__()``, as well as functions related to lock
    acquisition.

    The implementation for setting and retrieving the namespace data is
    handled by subclasses.

    NamespaceManager may be used alone, or may be accessed by
    one or more :class:`.Value` objects.  :class:`.Value` objects provide per-key
    services like expiration times and automatic recreation of values.

    Multiple NamespaceManagers created with a particular name will all
    share access to the same underlying datasource and will attempt to
    synchronize against a common mutex object.  The scope of this
    sharing may be within a single process or across multiple
    processes, depending on the type of NamespaceManager used.

    The NamespaceManager itself is generally threadsafe, except in the
    case of the DBMNamespaceManager in conjunction with the gdbm dbm
    implementation.

    """

    @classmethod
    def _init_dependencies(cls):
        """Initialize module-level dependent libraries required
        by this :class:`.NamespaceManager`."""

    def __init__(self, namespace):
        self._init_dependencies()
        self.namespace = namespace

    def get_creation_lock(self, key):
        """Return a locking object that is used to synchronize
        multiple threads or processes which wish to generate a new
        cache value.

        This function is typically an instance of
        :class:`.FileSynchronizer`, :class:`.ConditionSynchronizer`,
        or :class:`.null_synchronizer`.

        The creation lock is only used when a requested value
        does not exist, or has been expired, and is only used
        by the :class:`.Value` key-management object in conjunction
        with a "createfunc" value-creation function.

        """
        raise NotImplementedError()

    def do_remove(self):
        """Implement removal of the entire contents of this
        :class:`.NamespaceManager`.

        e.g. for a file-based namespace, this would remove
        all the files.

        The front-end to this method is the
        :meth:`.NamespaceManager.remove` method.

        """
        raise NotImplementedError()

    def acquire_read_lock(self):
        """Establish a read lock.

        This operation is called before a key is read.    By
        default the function does nothing.

        """

    def release_read_lock(self):
        """Release a read lock.

        This operation is called after a key is read.    By
        default the function does nothing.

        """

    def acquire_write_lock(self, wait=True, replace=False):
        """Establish a write lock.

        This operation is called before a key is written.
        A return value of ``True`` indicates the lock has
        been acquired.

        By default the function returns ``True`` unconditionally.

        'replace' is a hint indicating the full contents
        of the namespace may be safely discarded. Some backends
        may implement this (i.e. file backend won't unpickle the
        current contents).

        """
        return True

    def release_write_lock(self):
        """Release a write lock.

        This operation is called after a new value is written.
        By default this function does nothing.

        """

    def has_key(self, key):
        """Return ``True`` if the given key is present in this
        :class:`.Namespace`.
        """
        return self.__contains__(key)

    def __getitem__(self, key):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def set_value(self, key, value, expiretime=None):
        """Sets a value in this :class:`.NamespaceManager`.

        This is the same as ``__setitem__()``, but
        also allows an expiration time to be passed
        at the same time.

        """
        self[key] = value

    def __contains__(self, key):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def keys(self):
        """Return the list of all keys.

        This method may not be supported by all
        :class:`.NamespaceManager` implementations.

        """
        raise NotImplementedError()

    def remove(self):
        """Remove the entire contents of this
        :class:`.NamespaceManager`.

        e.g. for a file-based namespace, this would remove
        all the files.
        """
        self.do_remove()


class OpenResourceNamespaceManager(NamespaceManager):
    """A NamespaceManager where read/write operations require opening/
    closing of a resource which is possibly mutexed.

    """
    def __init__(self, namespace):
        NamespaceManager.__init__(self, namespace)
        self.access_lock = self.get_access_lock()
        self.openers = 0
        self.mutex = _threading.Lock()

    def get_access_lock(self):
        raise NotImplementedError()

    def do_open(self, flags, replace):
        raise NotImplementedError()

    def do_close(self):
        raise NotImplementedError()

    def acquire_read_lock(self):
        self.access_lock.acquire_read_lock()
        try:
            self.open('r', checkcount=True)
        except:
            self.access_lock.release_read_lock()
            raise

    def release_read_lock(self):
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_read_lock()

    def acquire_write_lock(self, wait=True, replace=False):
        r = self.access_lock.acquire_write_lock(wait)
        try:
            if (wait or r):
                self.open('c', checkcount=True, replace=replace)
            return r
        except:
            self.access_lock.release_write_lock()
            raise

    def release_write_lock(self):
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_write_lock()

    def open(self, flags, checkcount=False, replace=False):
        self.mutex.acquire()
        try:
            if checkcount:
                if self.openers == 0:
                    self.do_open(flags, replace)
                self.openers += 1
            else:
                self.do_open(flags, replace)
                self.openers = 1
        finally:
            self.mutex.release()

    def close(self, checkcount=False):
        self.mutex.acquire()
        try:
            if checkcount:
                self.openers -= 1
                if self.openers == 0:
                    self.do_close()
            else:
                if self.openers > 0:
                    self.do_close()
                self.openers = 0
        finally:
            self.mutex.release()

    def remove(self):
        self.access_lock.acquire_write_lock()
        try:
            self.close(checkcount=False)
            self.do_remove()
        finally:
            self.access_lock.release_write_lock()


class Value(object):
    """Implements synchronization, expiration, and value-creation logic
    for a single value stored in a :class:`.NamespaceManager`.

    """

    __slots__ = 'key', 'createfunc', 'expiretime', 'expire_argument', 'starttime', 'storedtime',\
                'namespace'

    def __init__(self, key, namespace, createfunc=None, expiretime=None, starttime=None):
        self.key = key
        self.createfunc = createfunc
        self.expire_argument = expiretime
        self.starttime = starttime
        self.storedtime = -1
        self.namespace = namespace

    def has_value(self):
        """return true if the container has a value stored.

        This is regardless of it being expired or not.

        """
        self.namespace.acquire_read_lock()
        try:
            return self.key in self.namespace
        finally:
            self.namespace.release_read_lock()

    def can_have_value(self):
        return self.has_current_value() or self.createfunc is not None

    def has_current_value(self):
        self.namespace.acquire_read_lock()
        try:
            has_value = self.key in self.namespace
            if has_value:
                try:
                    stored, expired, value = self._get_value()
                    return not self._is_expired(stored, expired)
                except KeyError:
                    pass
            return False
        finally:
            self.namespace.release_read_lock()

    def _is_expired(self, storedtime, expiretime):
        """Return true if this container's value is expired."""
        return (
            (
                self.starttime is not None and
                storedtime < self.starttime
            )
            or
            (
                expiretime is not None and
                time.time() >= expiretime + storedtime
            )
        )

    def get_value(self):
        self.namespace.acquire_read_lock()
        try:
            has_value = self.has_value()
            if has_value:
                try:
                    stored, expired, value = self._get_value()
                    if not self._is_expired(stored, expired):
                        return value
                except KeyError:
                    # guard against un-mutexed backends raising KeyError
                    has_value = False

            if not self.createfunc:
                raise KeyError(self.key)
        finally:
            self.namespace.release_read_lock()

        has_createlock = False
        creation_lock = self.namespace.get_creation_lock(self.key)
        if has_value:
            if not creation_lock.acquire(wait=False):
                debug("get_value returning old value while new one is created")
                return value
            else:
                debug("lock_creatfunc (didnt wait)")
                has_createlock = True

        if not has_createlock:
            debug("lock_createfunc (waiting)")
            creation_lock.acquire()
            debug("lock_createfunc (waited)")

        try:
            # see if someone created the value already
            self.namespace.acquire_read_lock()
            try:
                if self.has_value():
                    try:
                        stored, expired, value = self._get_value()
                        if not self._is_expired(stored, expired):
                            return value
                    except KeyError:
                        # guard against un-mutexed backends raising KeyError
                        pass
            finally:
                self.namespace.release_read_lock()

            debug("get_value creating new value")
            v = self.createfunc()
            self.set_value(v)
            return v
        finally:
            creation_lock.release()
            debug("released create lock")

    def _get_value(self):
        value = self.namespace[self.key]
        try:
            stored, expired, value = value
        except ValueError:
            if not len(value) == 2:
                raise
            # Old format: upgrade
            stored, value = value
            expired = self.expire_argument
            debug("get_value upgrading time %r expire time %r", stored, self.expire_argument)
            self.namespace.release_read_lock()
            self.set_value(value, stored)
            self.namespace.acquire_read_lock()
        except TypeError:
            # occurs when the value is None.  memcached
            # may yank the rug from under us in which case
            # that's the result
            raise KeyError(self.key)
        return stored, expired, value

    def set_value(self, value, storedtime=None):
        self.namespace.acquire_write_lock()
        try:
            if storedtime is None:
                storedtime = time.time()
            debug("set_value stored time %r expire time %r", storedtime, self.expire_argument)
            self.namespace.set_value(self.key, (storedtime, self.expire_argument, value),
                                     expiretime=self.expire_argument)
        finally:
            self.namespace.release_write_lock()

    def clear_value(self):
        self.namespace.acquire_write_lock()
        try:
            debug("clear_value")
            if self.key in self.namespace:
                try:
                    del self.namespace[self.key]
                except KeyError:
                    # guard against un-mutexed backends raising KeyError
                    pass
            self.storedtime = -1
        finally:
            self.namespace.release_write_lock()


class AbstractDictionaryNSManager(NamespaceManager):
    """A subclassable NamespaceManager that places data in a dictionary.

    Subclasses should provide a "dictionary" attribute or descriptor
    which returns a dict-like object.   The dictionary will store keys
    that are local to the "namespace" attribute of this manager, so
    ensure that the dictionary will not be used by any other namespace.

    e.g.::

        import collections
        cached_data = collections.defaultdict(dict)

        class MyDictionaryManager(AbstractDictionaryNSManager):
            def __init__(self, namespace):
                AbstractDictionaryNSManager.__init__(self, namespace)
                self.dictionary = cached_data[self.namespace]

    The above stores data in a global dictionary called "cached_data",
    which is structured as a dictionary of dictionaries, keyed
    first on namespace name to a sub-dictionary, then on actual
    cache key to value.

    """

    def get_creation_lock(self, key):
        return NameLock(
            identifier="memorynamespace/funclock/%s/%s" %
                        (self.namespace, key),
            reentrant=True
        )

    def __getitem__(self, key):
        return self.dictionary[key]

    def __contains__(self, key):
        return self.dictionary.__contains__(key)

    def has_key(self, key):
        return self.dictionary.__contains__(key)

    def __setitem__(self, key, value):
        self.dictionary[key] = value

    def __delitem__(self, key):
        del self.dictionary[key]

    def do_remove(self):
        self.dictionary.clear()

    def keys(self):
        return self.dictionary.keys()


class MemoryNamespaceManager(AbstractDictionaryNSManager):
    """:class:`.NamespaceManager` that uses a Python dictionary for storage."""

    namespaces = util.SyncDict()

    def __init__(self, namespace, **kwargs):
        AbstractDictionaryNSManager.__init__(self, namespace)
        self.dictionary = MemoryNamespaceManager.\
                                namespaces.get(self.namespace, dict)


class DBMNamespaceManager(OpenResourceNamespaceManager):
    """:class:`.NamespaceManager` that uses ``dbm`` files for storage."""

    def __init__(self, namespace, dbmmodule=None, data_dir=None,
            dbm_dir=None, lock_dir=None,
            digest_filenames=True, **kwargs):
        self.digest_filenames = digest_filenames

        if not dbm_dir and not data_dir:
            raise MissingCacheParameter("data_dir or dbm_dir is required")
        elif dbm_dir:
            self.dbm_dir = dbm_dir
        else:
            self.dbm_dir = data_dir + "/container_dbm"
        util.verify_directory(self.dbm_dir)

        if not lock_dir and not data_dir:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        elif lock_dir:
            self.lock_dir = lock_dir
        else:
            self.lock_dir = data_dir + "/container_dbm_lock"
        util.verify_directory(self.lock_dir)

        self.dbmmodule = dbmmodule or anydbm

        self.dbm = None
        OpenResourceNamespaceManager.__init__(self, namespace)

        self.file = util.encoded_path(root=self.dbm_dir,
                                      identifiers=[self.namespace],
                                      extension='.dbm',
                                      digest_filenames=self.digest_filenames)

        debug("data file %s", self.file)
        self._checkfile()

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace,
                                 lock_dir=self.lock_dir)

    def get_creation_lock(self, key):
        return file_synchronizer(
                    identifier="dbmcontainer/funclock/%s/%s" % (
                        self.namespace, key
                    ),
                    lock_dir=self.lock_dir
                )

    def file_exists(self, file):
        if os.access(file, os.F_OK):
            return True
        else:
            for ext in ('db', 'dat', 'pag', 'dir'):
                if os.access(file + os.extsep + ext, os.F_OK):
                    return True

        return False

    def _ensuredir(self, filename):
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            util.verify_directory(dirname)

    def _checkfile(self):
        if not self.file_exists(self.file):
            self._ensuredir(self.file)
            g = self.dbmmodule.open(self.file, 'c')
            g.close()

    def get_filenames(self):
        list = []
        if os.access(self.file, os.F_OK):
            list.append(self.file)

        for ext in ('pag', 'dir', 'db', 'dat'):
            if os.access(self.file + os.extsep + ext, os.F_OK):
                list.append(self.file + os.extsep + ext)
        return list

    def do_open(self, flags, replace):
        debug("opening dbm file %s", self.file)
        try:
            self.dbm = self.dbmmodule.open(self.file, flags)
        except:
            self._checkfile()
            self.dbm = self.dbmmodule.open(self.file, flags)

    def do_close(self):
        if self.dbm is not None:
            debug("closing dbm file %s", self.file)
            self.dbm.close()

    def do_remove(self):
        for f in self.get_filenames():
            os.remove(f)

    def __getitem__(self, key):
        return pickle.loads(self.dbm[key])

    def __contains__(self, key):
        if PYVER == (3, 2):
            # Looks like this is a bug that got solved in PY3.3 and PY3.4
            # http://bugs.python.org/issue19288
            if isinstance(key, unicode_text):
                key = key.encode('UTF-8')
        return key in self.dbm

    def __setitem__(self, key, value):
        self.dbm[key] = pickle.dumps(value)

    def __delitem__(self, key):
        del self.dbm[key]

    def keys(self):
        return self.dbm.keys()


class FileNamespaceManager(OpenResourceNamespaceManager):
    """:class:`.NamespaceManager` that uses binary files for storage.

    Each namespace is implemented as a single file storing a
    dictionary of key/value pairs, serialized using the Python
    ``pickle`` module.

    """
    def __init__(self, namespace, data_dir=None, file_dir=None, lock_dir=None,
                 digest_filenames=True, **kwargs):
        self.digest_filenames = digest_filenames

        if not file_dir and not data_dir:
            raise MissingCacheParameter("data_dir or file_dir is required")
        elif file_dir:
            self.file_dir = file_dir
        else:
            self.file_dir = data_dir + "/container_file"
        util.verify_directory(self.file_dir)

        if not lock_dir and not data_dir:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        elif lock_dir:
            self.lock_dir = lock_dir
        else:
            self.lock_dir = data_dir + "/container_file_lock"
        util.verify_directory(self.lock_dir)
        OpenResourceNamespaceManager.__init__(self, namespace)

        self.file = util.encoded_path(root=self.file_dir,
                                      identifiers=[self.namespace],
                                      extension='.cache',
                                      digest_filenames=self.digest_filenames)
        self.hash = {}

        debug("data file %s", self.file)

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace,
                                 lock_dir=self.lock_dir)

    def get_creation_lock(self, key):
        return file_synchronizer(
                identifier="dbmcontainer/funclock/%s/%s" % (
                    self.namespace, key
                ),
                lock_dir=self.lock_dir
                )

    def file_exists(self, file):
        return os.access(file, os.F_OK)

    def do_open(self, flags, replace):
        if not replace and self.file_exists(self.file):
            try:
                with open(self.file, 'rb') as fh:
                    self.hash = pickle.load(fh)
            except IOError as e:
                # Ignore EACCES and ENOENT as it just means we are no longer
                # able to access the file or that it no longer exists
                if e.errno not in [errno.EACCES, errno.ENOENT]:
                    raise

        self.flags = flags

    def do_close(self):
        if self.flags == 'c' or self.flags == 'w':
            pickled = pickle.dumps(self.hash)
            util.safe_write(self.file, pickled)

        self.hash = {}
        self.flags = None

    def do_remove(self):
        try:
            os.remove(self.file)
        except OSError:
            # for instance, because we haven't yet used this cache,
            # but client code has asked for a clear() operation...
            pass
        self.hash = {}

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


#### legacy stuff to support the old "Container" class interface

namespace_classes = {}

ContainerContext = dict


class ContainerMeta(type):
    def __init__(cls, classname, bases, dict_):
        namespace_classes[cls] = cls.namespace_class
        return type.__init__(cls, classname, bases, dict_)

    def __call__(self, key, context, namespace, createfunc=None,
                 expiretime=None, starttime=None, **kwargs):
        if namespace in context:
            ns = context[namespace]
        else:
            nscls = namespace_classes[self]
            context[namespace] = ns = nscls(namespace, **kwargs)
        return Value(key, ns, createfunc=createfunc,
                     expiretime=expiretime, starttime=starttime)

@add_metaclass(ContainerMeta)
class Container(object):
    """Implements synchronization and value-creation logic
    for a 'value' stored in a :class:`.NamespaceManager`.

    :class:`.Container` and its subclasses are deprecated.   The
    :class:`.Value` class is now used for this purpose.

    """
    namespace_class = NamespaceManager


class FileContainer(Container):
    namespace_class = FileNamespaceManager


class MemoryContainer(Container):
    namespace_class = MemoryNamespaceManager


class DBMContainer(Container):
    namespace_class = DBMNamespaceManager

DbmContainer = DBMContainer
