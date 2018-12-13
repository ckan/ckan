# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Module to find differences over time in a filesystem

Basically this takes a snapshot of a directory, then sees what changes
were made.  The contents of the files are not checked, so you can
detect that the content was changed, but not what the old version of
the file was.
"""

import os
from fnmatch import fnmatch
from datetime import datetime
from paste.util.UserDict24 import IterableUserDict
import operator
import re

__all__ = ['Diff', 'Snapshot', 'File', 'Dir', 'report_expected_diffs',
           'show_diff']

class Diff(object):

    """
    Represents the difference between two snapshots
    """

    def __init__(self, before, after):
        self.before = before
        self.after = after
        self._calculate()

    def _calculate(self):
        before = self.before.data
        after = self.after.data
        self.deleted = {}
        self.updated = {}
        self.created = after.copy()
        for path, f in before.items():
            if path not in after:
                self.deleted[path] = f
                continue
            del self.created[path]
            if f.mtime < after[path].mtime:
                self.updated[path] = after[path]

    def __str__(self):
        return self.report()

    def report(self, header=True, dates=False):
        s = []
        if header:
            s.append('Difference in %s from %s to %s:' %
                     (self.before.base_path,
                      self.before.calculated,
                      self.after.calculated))
        for name, files, show_size in [
            ('created', self.created, True),
            ('deleted', self.deleted, True),
            ('updated', self.updated, True)]:
            if files:
                s.append('-- %s: -------------------' % name)
                files = files.items()
                files.sort()
                last = ''
                for path, f in files:
                    t = '  %s' % _space_prefix(last, path, indent=4,
                                               include_sep=False)
                    last = path
                    if show_size and f.size != 'N/A':
                        t += '  (%s bytes)' % f.size
                    if dates:
                        parts = []
                        if self.before.get(path):
                            parts.append(self.before[path].mtime)
                        if self.after.get(path):
                            parts.append(self.after[path].mtime)
                        t += ' (mtime: %s)' % ('->'.join(map(repr, parts)))
                    s.append(t)
        if len(s) == 1:
            s.append('  (no changes)')
        return '\n'.join(s)

class Snapshot(IterableUserDict):

    """
    Represents a snapshot of a set of files.  Has a dictionary-like
    interface, keyed relative to ``base_path``
    """

    def __init__(self, base_path, files=None, ignore_wildcards=(),
                 ignore_paths=(), ignore_hidden=True):
        self.base_path = base_path
        self.ignore_wildcards = ignore_wildcards
        self.ignore_hidden = ignore_hidden
        self.ignore_paths = ignore_paths
        self.calculated = None
        self.data = files or {}
        if files is None:
            self.find_files()

    ############################################################
    ## File finding
    ############################################################

    def find_files(self):
        """
        Find all the files under the base path, and put them in
        ``self.data``
        """
        self._find_traverse('', self.data)
        self.calculated = datetime.now()

    def _ignore_file(self, fn):
        if fn in self.ignore_paths:
            return True
        if self.ignore_hidden and os.path.basename(fn).startswith('.'):
            return True
        for pat in self.ignore_wildcards:
            if fnmatch(fn, pat):
                return True
        return False

    def _ignore_file(self, fn):
        if fn in self.ignore_paths:
            return True
        if self.ignore_hidden and os.path.basename(fn).startswith('.'):
            return True
        return False

    def _find_traverse(self, path, result):
        full = os.path.join(self.base_path, path)
        if os.path.isdir(full):
            if path:
                # Don't actually include the base path
                result[path] = Dir(self.base_path, path)
            for fn in os.listdir(full):
                fn = os.path.join(path, fn)
                if self._ignore_file(fn):
                    continue
                self._find_traverse(fn, result)
        else:
            result[path] = File(self.base_path, path)

    def __repr__(self):
        return '<%s in %r from %r>' % (
            self.__class__.__name__, self.base_path,
            self.calculated or '(no calculation done)')

    def compare_expected(self, expected, comparison=operator.eq,
                         differ=None, not_found=None,
                         include_success=False):
        """
        Compares a dictionary of ``path: content`` to the
        found files.  Comparison is done by equality, or the
        ``comparison(actual_content, expected_content)`` function given.

        Returns dictionary of differences, keyed by path.  Each
        difference is either noted, or the output of
        ``differ(actual_content, expected_content)`` is given.

        If a file does not exist and ``not_found`` is given, then
        ``not_found(path)`` is put in.
        """
        result = {}
        for path in expected:
            orig_path = path
            path = path.strip('/')
            if path not in self.data:
                if not_found:
                    msg = not_found(path)
                else:
                    msg = 'not found'
                result[path] = msg
                continue
            expected_content = expected[orig_path]
            file = self.data[path]
            actual_content = file.bytes
            if not comparison(actual_content, expected_content):
                if differ:
                    msg = differ(actual_content, expected_content)
                else:
                    if len(actual_content) < len(expected_content):
                        msg = 'differ (%i bytes smaller)' % (
                            len(expected_content) - len(actual_content))
                    elif len(actual_content) > len(expected_content):
                        msg = 'differ (%i bytes larger)' % (
                            len(actual_content) - len(expected_content))
                    else:
                        msg = 'diff (same size)'
                result[path] = msg
            elif include_success:
                result[path] = 'same!'
        return result

    def diff_to_now(self):
        return Diff(self, self.clone())

    def clone(self):
        return self.__class__(base_path=self.base_path,
                              ignore_wildcards=self.ignore_wildcards,
                              ignore_paths=self.ignore_paths,
                              ignore_hidden=self.ignore_hidden)

class File(object):

    """
    Represents a single file found as the result of a command.

    Has attributes:

    ``path``:
        The path of the file, relative to the ``base_path``

    ``full``:
        The full path

    ``stat``:
        The results of ``os.stat``.  Also ``mtime`` and ``size``
        contain the ``.st_mtime`` and ``st_size`` of the stat.

    ``bytes``:
        The contents of the file.

    You may use the ``in`` operator with these objects (tested against
    the contents of the file), and the ``.mustcontain()`` method.
    """

    file = True
    dir = False

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.stat = os.stat(self.full)
        self.mtime = self.stat.st_mtime
        self.size = self.stat.st_size
        self._bytes = None

    def bytes__get(self):
        if self._bytes is None:
            f = open(self.full, 'rb')
            self._bytes = f.read()
            f.close()
        return self._bytes
    bytes = property(bytes__get)

    def __contains__(self, s):
        return s in self.bytes

    def mustcontain(self, s):
        __tracebackhide__ = True
        bytes = self.bytes
        if s not in bytes:
            print 'Could not find %r in:' % s
            print bytes
            assert s in bytes

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

class Dir(File):

    """
    Represents a directory created by a command.
    """

    file = False
    dir = True

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.size = 'N/A'
        self.mtime = 'N/A'

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

    def bytes__get(self):
        raise NotImplementedError(
            "Directory %r doesn't have content" % self)

    bytes = property(bytes__get)
    

def _space_prefix(pref, full, sep=None, indent=None, include_sep=True):
    """
    Anything shared by pref and full will be replaced with spaces
    in full, and full returned.

    Example::

        >>> _space_prefix('/foo/bar', '/foo')
        '    /bar'
    """
    if sep is None:
        sep = os.path.sep
    pref = pref.split(sep)
    full = full.split(sep)
    padding = []
    while pref and full and pref[0] == full[0]:
        if indent is None:
            padding.append(' ' * (len(full[0]) + len(sep)))
        else:
            padding.append(' ' * indent)
        full.pop(0)
        pref.pop(0)
    if padding:
        if include_sep:
            return ''.join(padding) + sep + sep.join(full)
        else:
            return ''.join(padding) + sep.join(full)
    else:
        return sep.join(full)

def report_expected_diffs(diffs, colorize=False):
    """
    Takes the output of compare_expected, and returns a string
    description of the differences.
    """
    if not diffs:
        return 'No differences'
    diffs = diffs.items()
    diffs.sort()
    s = []
    last = ''
    for path, desc in diffs:
        t = _space_prefix(last, path, indent=4, include_sep=False)
        if colorize:
            t = color_line(t, 11)
        last = path
        if len(desc.splitlines()) > 1:
            cur_indent = len(re.search(r'^[ ]*', t).group(0))
            desc = indent(cur_indent+2, desc)
            if colorize:
                t += '\n'
                for line in desc.splitlines():
                    if line.strip().startswith('+'):
                        line = color_line(line, 10)
                    elif line.strip().startswith('-'):
                        line = color_line(line, 9)
                    else:
                        line = color_line(line, 14)
                    t += line+'\n'
            else:
                t += '\n' + desc
        else:
            t += ' '+desc
        s.append(t)
    s.append('Files with differences: %s' % len(diffs))
    return '\n'.join(s)

def color_code(foreground=None, background=None):
    """
    0  black
    1  red
    2  green
    3  yellow
    4  blue
    5  magenta (purple)
    6  cyan
    7  white (gray)

    Add 8 to get high-intensity
    """
    if foreground is None and background is None:
        # Reset
        return '\x1b[0m'
    codes = []
    if foreground is None:
        codes.append('[39m')
    elif foreground > 7:
        codes.append('[1m')
        codes.append('[%im' % (22+foreground))
    else:
        codes.append('[%im' % (30+foreground))
    if background is None:
        codes.append('[49m')
    else:
        codes.append('[%im' % (40+background))
    return '\x1b' + '\x1b'.join(codes)

def color_line(line, foreground=None, background=None):
    match = re.search(r'^(\s*)', line)
    return (match.group(1) + color_code(foreground, background)
            + line[match.end():] + color_code())

def indent(indent, text):
    return '\n'.join(
        [' '*indent + l for l in text.splitlines()])

def show_diff(actual_content, expected_content):
    actual_lines = [l.strip() for l in actual_content.splitlines()
                    if l.strip()]
    expected_lines = [l.strip() for l in expected_content.splitlines()
                      if l.strip()]
    if len(actual_lines) == len(expected_lines) == 1:
        return '%r not %r' % (actual_lines[0], expected_lines[0])
    if not actual_lines:
        return 'Empty; should have:\n'+expected_content
    import difflib
    return '\n'.join(difflib.ndiff(actual_lines, expected_lines))
