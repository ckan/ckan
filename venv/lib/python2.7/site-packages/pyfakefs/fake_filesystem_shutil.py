#!/usr/bin/env python
#
# Copyright 2009 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A fake shutil module implementation that uses fake_filesystem for unit tests.

:Includes:
  FakeShutil: Uses a FakeFilesystem to provide a fake replacement for the
    shutil module.

:Usage:

>>> from pyfakefs import fake_filesystem
>>> from pyfakefs import fake_filesystem_shutil
>>> filesystem = fake_filesystem.FakeFilesystem()
>>> shutil_module = fake_filesystem_shutil.FakeShutilModule(filesystem)

Copy a fake_filesystem directory tree:

>>> new_file = filesystem.CreateFile('/src/new-file')
>>> shutil_module.copytree('/src', '/dst')
>>> filesystem.Exists('/dst/new-file')
True

Remove a fake_filesystem directory tree:

>>> shutil_module.rmtree('/src')
>>> filesystem.Exists('/src/new-file')
False
"""

import errno
import os
import shutil
import sys

import stat

__pychecker__ = 'no-reimportself'

_PERM_WRITE = 0o200  # Write permission bit.
_PERM_READ = 0o400   # Read permission bit.
_PERM_ALL = 0o7777   # All permission bits.


class FakeShutilModule(object):
    """Uses a FakeFilesystem to provide a fake replacement for shutil module."""

    def __init__(self, filesystem):
        """Construct fake shutil module using the fake filesystem.

        Args:
          filesystem:  FakeFilesystem used to provide file system information
        """
        self.filesystem = filesystem
        self._shutil_module = shutil

    def rmtree(self, path, ignore_errors=False, onerror=None):
        # Docstring from the real rmtree() documentation
        """Delete an entire directory tree; path must point to a directory (but not
        a symbolic link to a directory). If ignore_errors is true, errors resulting
        from failed removals will be ignored; if false or omitted, such errors are
        handled by calling a handler specified by onerror or, if that is omitted,
        they raise an exception.

        Args:
          path: (str) Directory tree to remove.
          ignore_errors: (bool) If ignore_errors is true, errors resulting from
                         failed removals will be ignored; if false or omitted, such
                         errors are handled by calling a handler specified by
                         onerror.
                         New in pyfakefs 2.9.
          onerror: (func) If onerror is provided, it must be a callable that accepts
                   three parameters: function, path, and excinfo.

                   The first parameter, function, is the function which raised the
                   exception; it depends on the platform and implementation. The
                   second parameter, path, will be the path name passed to function.
                   The third parameter, excinfo, will be the exception information
                   returned by sys.exc_info(). Exceptions raised by onerror will not
                   be caught.
                   New in pyfakefs 2.9.
        """
        if ignore_errors:
            def onerror(*args):  # pylint: disable=unused-argument,function-redefined
                pass
        try:
            if not self.filesystem.Exists(path):
                raise IOError("The specified path does not exist")
            if stat.S_ISLNK(self.filesystem.GetObject(path).st_mode):
                # symlinks to directories are forbidden.
                raise OSError("Cannot call rmtree on a symbolic link")
        except Exception:
            if onerror is None:
                raise
            onerror(os.path.islink, path, sys.exc_info())
            # can't continue even if onerror hook returns
            return
        try:
            self.filesystem.RemoveObject(path)
        except (IOError, OSError):
            if onerror is None:
                raise
            onerror(FakeShutilModule.rmtree, path, sys.exc_info())

    def copy(self, src, dst):
        """Copy data and mode bits ("cp src dst").

        Args:
          src: (str) source file
          dst: (str) destination, may be a directory
        """
        if self.filesystem.Exists(dst):
            if stat.S_ISDIR(self.filesystem.GetObject(dst).st_mode):
                dst = self.filesystem.JoinPaths(dst, os.path.basename(src))
        self.copyfile(src, dst)
        src_object = self.filesystem.GetObject(src)
        dst_object = self.filesystem.GetObject(dst)
        dst_object.st_mode = ((dst_object.st_mode & ~_PERM_ALL) |
                              (src_object.st_mode & _PERM_ALL))

    def copyfile(self, src, dst):
        """Copy data from src to dst.

        Args:
          src: (str) source file
          dst: (dst) destination file

        Raises:
          IOError: if the file can't be copied
          shutil.Error: if the src and dst files are the same
        """
        src_file_object = self.filesystem.GetObject(src)
        if not src_file_object.st_mode & _PERM_READ:
            raise IOError(errno.EACCES, 'Permission denied', src)
        if stat.S_ISDIR(src_file_object.st_mode):
            raise IOError(errno.EISDIR, 'Is a directory', src)

        dst_dir = os.path.dirname(dst)
        if dst_dir:
            if not self.filesystem.Exists(dst_dir):
                raise IOError(errno.ENOTDIR, 'Not a directory', dst)
            dst_dir_object = self.filesystem.GetObject(dst_dir)
            if not dst_dir_object.st_mode & _PERM_WRITE:
                raise IOError(errno.EACCES, 'Permission denied', dst_dir)

        abspath_src = self.filesystem.NormalizePath(
            self.filesystem.ResolvePath(src))
        abspath_dst = self.filesystem.NormalizePath(
            self.filesystem.ResolvePath(dst))
        if abspath_src == abspath_dst:
            raise shutil.Error('`%s` and `%s` are the same file' % (src, dst))

        if self.filesystem.Exists(dst):
            dst_file_object = self.filesystem.GetObject(dst)
            if stat.S_ISDIR(dst_file_object.st_mode):
                raise IOError(errno.EISDIR, 'Is a directory', dst)
            if not dst_file_object.st_mode & _PERM_WRITE:
                raise IOError(errno.EACCES, 'Permission denied', dst)
            dst_file_object.SetContents(src_file_object.contents)

        else:
            self.filesystem.CreateFile(dst, contents=src_file_object.contents)

    def copystat(self, src, dst):
        """Copy all stat info (mode bits, atime, and mtime) from src to dst.

        Args:
          src: (str) source file
          dst: (str) destination file
        """
        src_object = self.filesystem.GetObject(src)
        dst_object = self.filesystem.GetObject(dst)
        dst_object.st_mode = ((dst_object.st_mode & ~_PERM_ALL) |
                              (src_object.st_mode & _PERM_ALL))
        dst_object.st_uid = src_object.st_uid
        dst_object.st_gid = src_object.st_gid
        dst_object.st_atime = src_object.st_atime
        dst_object.st_mtime = src_object.st_mtime

    def copy2(self, src, dst):
        """Copy data and all stat info ("cp -p src dst").

        Args:
          src: (str) source file
          dst: (str) destination, may be a directory
        """
        if self.filesystem.Exists(dst):
            if stat.S_ISDIR(self.filesystem.GetObject(dst).st_mode):
                dst = self.filesystem.JoinPaths(dst, os.path.basename(src))
        self.copyfile(src, dst)
        self.copystat(src, dst)

    def _copytree(self, src, dst, copy_function, symlinks):
        self.filesystem.CreateDirectory(dst)
        try:
            directory = self.filesystem.GetObject(src)
        except IOError as exception:
            raise OSError(exception.errno, exception.message)
        if not stat.S_ISDIR(directory.st_mode):
            raise OSError(errno.ENOTDIR,
                          'Fake os module: %r not a directory' % src)
        for name in directory.contents:
            srcname = self.filesystem.JoinPaths(src, name)
            dstname = self.filesystem.JoinPaths(dst, name)
            src_mode = self.filesystem.GetObject(srcname).st_mode
            if stat.S_ISDIR(src_mode):
                self._copytree(srcname, dstname, copy_function=copy_function, symlinks=symlinks)
            else:
                copy_function(srcname, dstname)

    # argument order changed between versions, have to use separate definitions
    if sys.version_info < (3, 2):
        def copytree(self, src, dst, symlinks=False):
            """Recursively copy a directory tree.

            Args:
              src: (str) source directory
              dst: (str) destination directory, must not already exist
              symlinks: (bool) copy symlinks as symlinks instead of copying the
                        contents of the linked files. Currently unused.

            Raises:
              OSError: if src is missing or isn't a directory
            """
            self._copytree(src, dst, copy_function=self.copy2, symlinks=symlinks)
    else:
        def copytree(self, src, dst, copy_function=None, symlinks=False):
            """Recursively copy a directory tree.

            Args:
              src: (str) source directory
              dst: (str) destination directory, must not already exist
              copy_function: replacement for copy2.
                New in python 3.2. New in pyfakefs 2.9.
              symlinks: (bool) copy symlinks as symlinks instead of copying the
                        contents of the linked files. Currently unused.

            Raises:
              OSError: if src is missing or isn't a directory
            """
            copy_function = copy_function or self.copy2
            self._copytree(src, dst, copy_function=copy_function, symlinks=symlinks)

    def move(self, src, dst, copy_function=None):
        """Rename a file or directory.

        Args:
          src: (str) source file or directory
          dst: (str) if the src is a directory, the dst must not already exist
          copy_function: replacement for copy2 if copying is needed.
            New in Python 3.5. New in pyfakefs 2.9.
        """

        def _destinsrc(src, dst):
            src = os.path.abspath(src)
            dst = os.path.abspath(dst)
            if not src.endswith(self.filesystem.path_separator):
                src += os.path.sep
            if not dst.endswith(self.filesystem.path_separator):
                dst += self.filesystem.path_separator
            return dst.startswith(src)

        if copy_function is not None:
            if sys.version_info < (3, 5):
                raise TypeError("move() got an unexpected keyword argument 'copy_function")
        else:
            copy_function = self.copy2

        src = self.filesystem.NormalizePath(src)
        dst = self.filesystem.NormalizePath(dst)
        if src == dst:
            return dst

        source_is_dir = stat.S_ISDIR(self.filesystem.GetObject(src).st_mode)
        if source_is_dir:
            dst = self.filesystem.JoinPaths(dst, os.path.basename(src))
            if self.filesystem.Exists(dst):
                raise shutil.Error("Destination path '%s' already exists" % dst)

        try:
            self.filesystem.RenameObject(src, dst)
        except OSError:
            if source_is_dir:
                if _destinsrc(src, dst):
                    raise shutil.Error("Cannot move a directory '%s' into itself"
                                       " '%s'." % (src, dst))
                self._copytree(src, dst, copy_function=copy_function, symlinks=True)
                self.rmtree(src)
            else:
                copy_function(src, dst)
                self.filesystem.RemoveObject(src)
        return dst

    if sys.version_info >= (3, 3):
        def disk_usage(self, path):
            """Return the total, used and free disk space in bytes as named tuple
            or placeholder holder values simulating unlimited space if not set.
            New in Python 3.3. New in pyfakefs 2.9.

            Args:
              path: defines the filesystem device which is queried
            """
            return self.filesystem.GetDiskUsage(path)

    def __getattr__(self, name):
        """Forwards any non-faked calls to the standard shutil module."""
        return getattr(self._shutil_module, name)


def _RunDoctest():
    # pylint: disable=import-self
    import doctest
    from pyfakefs import fake_filesystem_shutil
    return doctest.testmod(fake_filesystem_shutil)


if __name__ == '__main__':
    _RunDoctest()
