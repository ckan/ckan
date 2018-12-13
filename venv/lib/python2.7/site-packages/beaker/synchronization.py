"""Synchronization functions.

File- and mutex-based mutual exclusion synchronizers are provided,
as well as a name-based mutex which locks within an application
based on a string name.

"""
import errno
import os
import sys
import tempfile

try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

# check for fcntl module
try:
    sys.getwindowsversion()
    has_flock = False
except:
    try:
        import fcntl
        has_flock = True
    except ImportError:
        has_flock = False

from beaker import util
from beaker.exceptions import LockError

__all__ = ["file_synchronizer", "mutex_synchronizer", "null_synchronizer",
            "NameLock", "_threading"]


class NameLock(object):
    """a proxy for an RLock object that is stored in a name based
    registry.

    Multiple threads can get a reference to the same RLock based on the
    name alone, and synchronize operations related to that name.

    """
    locks = util.WeakValuedRegistry()

    class NLContainer(object):
        def __init__(self, reentrant):
            if reentrant:
                self.lock = _threading.RLock()
            else:
                self.lock = _threading.Lock()

        def __call__(self):
            return self.lock

    def __init__(self, identifier=None, reentrant=False):
        if identifier is None:
            self._lock = NameLock.NLContainer(reentrant)
        else:
            self._lock = NameLock.locks.get(identifier, NameLock.NLContainer,
                                            reentrant)

    def acquire(self, wait=True):
        return self._lock().acquire(wait)

    def release(self):
        self._lock().release()


_synchronizers = util.WeakValuedRegistry()


def _synchronizer(identifier, cls, **kwargs):
    return _synchronizers.sync_get((identifier, cls), cls, identifier, **kwargs)


def file_synchronizer(identifier, **kwargs):
    if not has_flock or 'lock_dir' not in kwargs:
        return mutex_synchronizer(identifier)
    else:
        return _synchronizer(identifier, FileSynchronizer, **kwargs)


def mutex_synchronizer(identifier, **kwargs):
    return _synchronizer(identifier, ConditionSynchronizer, **kwargs)


class null_synchronizer(object):
    """A 'null' synchronizer, which provides the :class:`.SynchronizerImpl` interface
    without any locking.

    """
    def acquire_write_lock(self, wait=True):
        return True

    def acquire_read_lock(self):
        pass

    def release_write_lock(self):
        pass

    def release_read_lock(self):
        pass
    acquire = acquire_write_lock
    release = release_write_lock


class SynchronizerImpl(object):
    """Base class for a synchronization object that allows
    multiple readers, single writers.

    """
    def __init__(self):
        self._state = util.ThreadLocal()

    class SyncState(object):
        __slots__ = 'reentrantcount', 'writing', 'reading'

        def __init__(self):
            self.reentrantcount = 0
            self.writing = False
            self.reading = False

    def state(self):
        if not self._state.has():
            state = SynchronizerImpl.SyncState()
            self._state.put(state)
            return state
        else:
            return self._state.get()
    state = property(state)

    def release_read_lock(self):
        state = self.state

        if state.writing:
            raise LockError("lock is in writing state")
        if not state.reading:
            raise LockError("lock is not in reading state")

        if state.reentrantcount == 1:
            self.do_release_read_lock()
            state.reading = False

        state.reentrantcount -= 1

    def acquire_read_lock(self, wait=True):
        state = self.state

        if state.writing:
            raise LockError("lock is in writing state")

        if state.reentrantcount == 0:
            x = self.do_acquire_read_lock(wait)
            if (wait or x):
                state.reentrantcount += 1
                state.reading = True
            return x
        elif state.reading:
            state.reentrantcount += 1
            return True

    def release_write_lock(self):
        state = self.state

        if state.reading:
            raise LockError("lock is in reading state")
        if not state.writing:
            raise LockError("lock is not in writing state")

        if state.reentrantcount == 1:
            self.do_release_write_lock()
            state.writing = False

        state.reentrantcount -= 1

    release = release_write_lock

    def acquire_write_lock(self, wait=True):
        state = self.state

        if state.reading:
            raise LockError("lock is in reading state")

        if state.reentrantcount == 0:
            x = self.do_acquire_write_lock(wait)
            if (wait or x):
                state.reentrantcount += 1
                state.writing = True
            return x
        elif state.writing:
            state.reentrantcount += 1
            return True

    acquire = acquire_write_lock

    def do_release_read_lock(self):
        raise NotImplementedError()

    def do_acquire_read_lock(self, wait):
        raise NotImplementedError()

    def do_release_write_lock(self):
        raise NotImplementedError()

    def do_acquire_write_lock(self, wait):
        raise NotImplementedError()


class FileSynchronizer(SynchronizerImpl):
    """A synchronizer which locks using flock().

    """
    def __init__(self, identifier, lock_dir):
        super(FileSynchronizer, self).__init__()
        self._filedescriptor = util.ThreadLocal()

        if lock_dir is None:
            lock_dir = tempfile.gettempdir()
        else:
            lock_dir = lock_dir

        self.filename = util.encoded_path(
                            lock_dir,
                            [identifier],
                            extension='.lock'
                        )
        self.lock_dir = os.path.dirname(self.filename)

    def _filedesc(self):
        return self._filedescriptor.get()
    _filedesc = property(_filedesc)

    def _ensuredir(self):
        if not os.path.exists(self.lock_dir):
            util.verify_directory(self.lock_dir)

    def _open(self, mode):
        filedescriptor = self._filedesc
        if filedescriptor is None:
            self._ensuredir()
            filedescriptor = os.open(self.filename, mode)
            self._filedescriptor.put(filedescriptor)
        return filedescriptor

    def do_acquire_read_lock(self, wait):
        filedescriptor = self._open(os.O_CREAT | os.O_RDONLY)
        if not wait:
            try:
                fcntl.flock(filedescriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
                return True
            except IOError:
                os.close(filedescriptor)
                self._filedescriptor.remove()
                return False
        else:
            fcntl.flock(filedescriptor, fcntl.LOCK_SH)
            return True

    def do_acquire_write_lock(self, wait):
        filedescriptor = self._open(os.O_CREAT | os.O_WRONLY)
        if not wait:
            try:
                fcntl.flock(filedescriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                os.close(filedescriptor)
                self._filedescriptor.remove()
                return False
        else:
            fcntl.flock(filedescriptor, fcntl.LOCK_EX)
            return True

    def do_release_read_lock(self):
        self._release_all_locks()

    def do_release_write_lock(self):
        self._release_all_locks()

    def _release_all_locks(self):
        filedescriptor = self._filedesc
        if filedescriptor is not None:
            fcntl.flock(filedescriptor, fcntl.LOCK_UN)
            os.close(filedescriptor)
            self._filedescriptor.remove()


class ConditionSynchronizer(SynchronizerImpl):
    """a synchronizer using a Condition."""

    def __init__(self, identifier):
        super(ConditionSynchronizer, self).__init__()

        # counts how many asynchronous methods are executing
        self.asynch = 0

        # pointer to thread that is the current sync operation
        self.current_sync_operation = None

        # condition object to lock on
        self.condition = _threading.Condition(_threading.Lock())

    def do_acquire_read_lock(self, wait=True):
        self.condition.acquire()
        try:
            # see if a synchronous operation is waiting to start
            # or is already running, in which case we wait (or just
            # give up and return)
            if wait:
                while self.current_sync_operation is not None:
                    self.condition.wait()
            else:
                if self.current_sync_operation is not None:
                    return False

            self.asynch += 1
        finally:
            self.condition.release()

        if not wait:
            return True

    def do_release_read_lock(self):
        self.condition.acquire()
        try:
            self.asynch -= 1

            # check if we are the last asynchronous reader thread
            # out the door.
            if self.asynch == 0:
                # yes. so if a sync operation is waiting, notifyAll to wake
                # it up
                if self.current_sync_operation is not None:
                    self.condition.notifyAll()
            elif self.asynch < 0:
                raise LockError("Synchronizer error - too many "
                                "release_read_locks called")
        finally:
            self.condition.release()

    def do_acquire_write_lock(self, wait=True):
        self.condition.acquire()
        try:
            # here, we are not a synchronous reader, and after returning,
            # assuming waiting or immediate availability, we will be.

            if wait:
                # if another sync is working, wait
                while self.current_sync_operation is not None:
                    self.condition.wait()
            else:
                # if another sync is working,
                # we dont want to wait, so forget it
                if self.current_sync_operation is not None:
                    return False

            # establish ourselves as the current sync
            # this indicates to other read/write operations
            # that they should wait until this is None again
            self.current_sync_operation = _threading.currentThread()

            # now wait again for asyncs to finish
            if self.asynch > 0:
                if wait:
                    # wait
                    self.condition.wait()
                else:
                    # we dont want to wait, so forget it
                    self.current_sync_operation = None
                    return False
        finally:
            self.condition.release()

        if not wait:
            return True

    def do_release_write_lock(self):
        self.condition.acquire()
        try:
            if self.current_sync_operation is not _threading.currentThread():
                raise LockError("Synchronizer error - current thread doesnt "
                                "have the write lock")

            # reset the current sync operation so
            # another can get it
            self.current_sync_operation = None

            # tell everyone to get ready
            self.condition.notifyAll()
        finally:
            # everyone go !!
            self.condition.release()
