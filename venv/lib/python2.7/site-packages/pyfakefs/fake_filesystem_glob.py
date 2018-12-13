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

"""A fake glob module implementation that uses fake_filesystem for unit tests.

Includes:
  FakeGlob: Uses a FakeFilesystem to provide a fake replacement for the
    glob module.
Note: Code is taken form Python 3.5 and slightly adapted to work with older
    versions and use the fake os and os.path modules

:Usage:

>>> from pyfakefs import fake_filesystem
>>> from pyfakefs import fake_filesystem_glob
>>> filesystem = fake_filesystem.FakeFilesystem()
>>> glob_module = fake_filesystem_glob.FakeGlobModule(filesystem)

>>> file = filesystem.CreateFile('new-file')
>>> glob_module.glob('*')
['new-file']
>>> glob_module.glob('???-file')
['new-file']
"""

import fnmatch
import glob
import re
import sys

from pyfakefs import fake_filesystem


class FakeGlobModule(object):
    """Uses a FakeFilesystem to provide a fake replacement for glob module."""

    def __init__(self, filesystem):
        """Construct fake glob module using the fake filesystem.

        Args:
          filesystem:  FakeFilesystem used to provide file system information
        """
        self._glob_module = glob
        self._os_module = fake_filesystem.FakeOsModule(filesystem)
        self._path_module = self._os_module.path
        self._filesystem = filesystem

    def glob(self, pathname, recursive=None):
        """Return a list of paths matching a pathname pattern.

        The pattern may contain shell-style wildcards a la fnmatch.

        Args:
            pathname: the pattern with which to find a list of paths.
            recursive: if true, the pattern '**' will match any files and
            zero or more directories and subdirectories.
            New in Python 3.5. New in pyfakefs 3.0.

        Returns:
            List of strings matching the glob pattern.
        """
        return list(
            self.iglob(pathname, recursive=_recursive_from_arg(recursive)))

    def iglob(self, pathname, recursive=None):
        """Return an iterator yielding the paths matching a pathname pattern.
        New in pyfakefs 3.0.

        The pattern may contain shell-style wildcards a la fnmatch.

        Args:
            pathname: the pattern with which to find a list of paths.
            recursive: if true, the pattern '**' will match any files and
            zero or more directories and subdirectories. New in Python 3.5.
        """
        recursive = _recursive_from_arg(recursive)
        itr = self._iglob(pathname, recursive)
        if recursive and _isrecursive(pathname):
            string = next(itr)  # skip empty string
            assert not string
        return itr

    def _iglob(self, pathname, recursive):
        dirname, basename = self._path_module.split(pathname)
        if not self.has_magic(pathname):
            if basename:
                if self._path_module.lexists(pathname):
                    yield pathname
            else:
                # Patterns ending with a slash should match only directories
                if self._path_module.isdir(dirname):
                    yield pathname
            return
        if not dirname:
            if recursive and _isrecursive(basename):
                for name in self.glob2(dirname, basename):
                    yield name
            else:
                for name in self.glob1(dirname, basename):
                    yield name
            return
        # `self._path_module.split()` returns the argument itself as a dirname
        # if it is a drive or UNC path.
        # Prevent an infinite recursion if a drive or UNC path
        # contains magic characters (i.e. r'\\?\C:').
        if dirname != pathname and self.has_magic(dirname):
            dirs = self._iglob(dirname, recursive)
        else:
            dirs = [dirname]
        if self.has_magic(basename):
            if recursive and _isrecursive(basename):
                glob_in_dir = self.glob2
            else:
                glob_in_dir = self.glob1
        else:
            glob_in_dir = self.glob0
        for dirname in dirs:
            for name in glob_in_dir(dirname, basename):
                yield self._path_module.join(dirname, name)

    # These 2 helper functions non-recursively glob inside a literal directory.
    # They return a list of basenames. `glob1` accepts a pattern while `glob0`
    # takes a literal basename (so it only has to check for its existence).
    def glob1(self, dirname, pattern):
        """Return a list of paths matching a pattern inside the given path non-recursively.

        Args:
            dirname: the directory where to look for the paths.
            pattern: the pattern with which to find a list of paths.

        Returns:
            List of strings matching the pattern.
        """
        if not dirname:
            # pylint: disable=undefined-variable
            if sys.version_info >= (3,) and isinstance(pattern, bytes):
                dirname = bytes(self._os_module.curdir, 'ASCII')
            elif sys.version_info < (3,) and isinstance(pattern, unicode):
                dirname = unicode(
                    self._os_module.curdir,
                    sys.getfilesystemencoding() or sys.getdefaultencoding())
            else:
                dirname = self._os_module.curdir

        try:
            names = self._os_module.listdir(dirname)
        except OSError:
            return []
        if not _ishidden(pattern):
            names = [x for x in names if not _ishidden(x)]
        return fnmatch.filter(names, pattern)

    def glob0(self, dirname, basename):
        """Return a list with the given basename if it exists.

        Args:
            dirname: the directory where to look for the path.
            basename: the name of the looked up directory.

        Returns:
            List containing the matching path or empty list.
        """
        if not basename:
            # `self._path_module.split()` returns an empty basename
            # for paths ending with a directory separator.
            # 'q*x/' should match only directories.
            if self._path_module.isdir(dirname):
                return [basename]
        else:
            if self._path_module.lexists(
                    self._path_module.join(dirname, basename)):
                return [basename]
        return []

    # This helper function recursively yields relative pathnames
    # inside a literal directory.
    def glob2(self, dirname, pattern):
        """Return a list of paths matching a pattern inside the given path recursively.

        Args:
            dirname: the top=level directory where to look for the paths.
            pattern: the pattern with which to find a list of paths.

        Returns:
            List of strings matching the pattern.
        """
        assert _isrecursive(pattern)
        yield pattern[:0]
        for path_name in self._rlistdir(dirname):
            yield path_name

    # Recursively yields relative pathnames inside a literal directory.
    def _rlistdir(self, dirname):
        if not dirname:
            # pylint: disable=undefined-variable
            if sys.version_info >= (3,) and isinstance(dirname, bytes):
                dirname = bytes(self._os_module.curdir, 'ASCII')
            elif sys.version_info < (3,) and isinstance(dirname, unicode):
                dirname = unicode(
                    self._os_module.curdir,
                    sys.getfilesystemencoding() or sys.getdefaultencoding())
            else:
                dirname = self._os_module.curdir

        try:
            names = self._os_module.listdir(dirname)
        except self._os_module.error:
            return
        for name in names:
            if not _ishidden(name):
                yield name
                path = self._path_module.join(dirname,
                                              name) if dirname else name
                for dir_name in self._rlistdir(path):
                    yield self._path_module.join(name, dir_name)

    magic_check = re.compile('([*?[])')
    magic_check_bytes = re.compile(b'([*?[])')

    def has_magic(self, string):
        """Return True if the given string contains placeholder characters."""
        if isinstance(string, bytes):
            match = self.magic_check_bytes.search(string)
        else:
            match = self.magic_check.search(string)
        return match is not None

    def escape(self, pathname):
        """Escape all special characters.
        """
        # Escaping is done by wrapping any of "*?[" between square brackets.
        # Metacharacters do not work in the drive part and shouldn't be escaped.
        drive, pathname = self._path_module.splitdrive(pathname)
        if isinstance(pathname, bytes):
            pathname = self.magic_check_bytes.sub(br'[\1]', pathname)
        else:
            pathname = self.magic_check.sub(r'[\1]', pathname)
        return drive + pathname

    def __getattr__(self, name):
        """Forwards any non-faked calls to the standard glob module."""
        return getattr(self._glob_module, name)


def _ishidden(path):
    return path[0] in ('.', b'.'[0])


def _isrecursive(pattern):
    if isinstance(pattern, bytes):
        return pattern == b'**'
    else:
        return pattern == '**'


def _recursive_from_arg(recursive):
    if sys.version_info >= (3, 5):
        if recursive is None:
            return False
        return recursive
    if recursive is not None:
        raise TypeError("glob() got an unexpected keyword argument 'recursive'")


def _RunDoctest():
    # pylint: disable=import-self
    import doctest
    from pyfakefs import fake_filesystem_glob
    return doctest.testmod(fake_filesystem_glob)


if __name__ == '__main__':
    _RunDoctest()
