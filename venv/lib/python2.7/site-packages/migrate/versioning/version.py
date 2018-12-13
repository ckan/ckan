#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import shutil
import logging

from migrate import exceptions
from migrate.versioning import pathed, script
from datetime import datetime
import six


log = logging.getLogger(__name__)

class VerNum(object):
    """A version number that behaves like a string and int at the same time"""

    _instances = dict()

    def __new__(cls, value):
        val = str(value)
        if val not in cls._instances:
            cls._instances[val] = super(VerNum, cls).__new__(cls)
        ret = cls._instances[val]
        return ret

    def __init__(self,value):
        self.value = str(int(value))
        if self < 0:
            raise ValueError("Version number cannot be negative")

    def __add__(self, value):
        ret = int(self) + int(value)
        return VerNum(ret)

    def __sub__(self, value):
        return self + (int(value) * -1)

    def __eq__(self, value):
        return int(self) == int(value)

    def __ne__(self, value):
        return int(self) != int(value)

    def __lt__(self, value):
        return int(self) < int(value)

    def __gt__(self, value):
        return int(self) > int(value)

    def __ge__(self, value):
        return int(self) >= int(value)

    def __le__(self, value):
        return int(self) <= int(value)

    def __repr__(self):
        return "<VerNum(%s)>" % self.value

    def __str__(self):
        return str(self.value)

    def __int__(self):
        return int(self.value)

    def __index__(self):
        return int(self.value)

    if six.PY3:
        def __hash__(self):
            return hash(self.value)


class Collection(pathed.Pathed):
    """A collection of versioning scripts in a repository"""

    FILENAME_WITH_VERSION = re.compile(r'^(\d{3,}).*')

    def __init__(self, path):
        """Collect current version scripts in repository
        and store them in self.versions
        """
        super(Collection, self).__init__(path)

        # Create temporary list of files, allowing skipped version numbers.
        files = os.listdir(path)
        if '1' in files:
            # deprecation
            raise Exception('It looks like you have a repository in the old '
                'format (with directories for each version). '
                'Please convert repository before proceeding.')

        tempVersions = dict()
        for filename in files:
            match = self.FILENAME_WITH_VERSION.match(filename)
            if match:
                num = int(match.group(1))
                tempVersions.setdefault(num, []).append(filename)
            else:
                pass  # Must be a helper file or something, let's ignore it.

        # Create the versions member where the keys
        # are VerNum's and the values are Version's.
        self.versions = dict()
        for num, files in tempVersions.items():
            self.versions[VerNum(num)] = Version(num, path, files)

    @property
    def latest(self):
        """:returns: Latest version in Collection"""
        return max([VerNum(0)] + list(self.versions.keys()))

    def _next_ver_num(self, use_timestamp_numbering):
        if use_timestamp_numbering == True:
            return VerNum(int(datetime.utcnow().strftime('%Y%m%d%H%M%S')))
        else:
            return self.latest + 1

    def create_new_python_version(self, description, **k):
        """Create Python files for new version"""
        ver = self._next_ver_num(k.pop('use_timestamp_numbering', False))
        extra = str_to_filename(description)

        if extra:
            if extra == '_':
                extra = ''
            elif not extra.startswith('_'):
                extra = '_%s' % extra

        filename = '%03d%s.py' % (ver, extra)
        filepath = self._version_path(filename)

        script.PythonScript.create(filepath, **k)
        self.versions[ver] = Version(ver, self.path, [filename])

    def create_new_sql_version(self, database, description, **k):
        """Create SQL files for new version"""
        ver = self._next_ver_num(k.pop('use_timestamp_numbering', False))
        self.versions[ver] = Version(ver, self.path, [])

        extra = str_to_filename(description)

        if extra:
            if extra == '_':
                extra = ''
            elif not extra.startswith('_'):
                extra = '_%s' % extra

        # Create new files.
        for op in ('upgrade', 'downgrade'):
            filename = '%03d%s_%s_%s.sql' % (ver, extra, database, op)
            filepath = self._version_path(filename)
            script.SqlScript.create(filepath, **k)
            self.versions[ver].add_script(filepath)

    def version(self, vernum=None):
        """Returns latest Version if vernum is not given.
        Otherwise, returns wanted version"""
        if vernum is None:
            vernum = self.latest
        return self.versions[VerNum(vernum)]

    @classmethod
    def clear(cls):
        super(Collection, cls).clear()

    def _version_path(self, ver):
        """Returns path of file in versions repository"""
        return os.path.join(self.path, str(ver))


class Version(object):
    """A single version in a collection
    :param vernum: Version Number
    :param path: Path to script files
    :param filelist: List of scripts
    :type vernum: int, VerNum
    :type path: string
    :type filelist: list
    """

    def __init__(self, vernum, path, filelist):
        self.version = VerNum(vernum)

        # Collect scripts in this folder
        self.sql = dict()
        self.python = None

        for script in filelist:
            self.add_script(os.path.join(path, script))

    def script(self, database=None, operation=None):
        """Returns SQL or Python Script"""
        for db in (database, 'default'):
            # Try to return a .sql script first
            try:
                return self.sql[db][operation]
            except KeyError:
                continue  # No .sql script exists

        # TODO: maybe add force Python parameter?
        ret = self.python

        assert ret is not None, \
            "There is no script for %d version" % self.version
        return ret

    def add_script(self, path):
        """Add script to Collection/Version"""
        if path.endswith(Extensions.py):
            self._add_script_py(path)
        elif path.endswith(Extensions.sql):
            self._add_script_sql(path)

    SQL_FILENAME = re.compile(r'^.*\.sql')

    def _add_script_sql(self, path):
        basename = os.path.basename(path)
        match = self.SQL_FILENAME.match(basename)

        if match:
            basename = basename.replace('.sql', '')
            parts = basename.split('_')
            if len(parts) < 3:
                raise exceptions.ScriptError(
                    "Invalid SQL script name %s " % basename + \
                    "(needs to be ###_description_database_operation.sql)")
            version = parts[0]
            op = parts[-1]
            # NOTE(mriedem): check for ibm_db_sa as the database in the name
            if 'ibm_db_sa' in basename:
                if len(parts) == 6:
                    dbms = '_'.join(parts[-4: -1])
                else:
                    raise exceptions.ScriptError(
                        "Invalid ibm_db_sa SQL script name '%s'; "
                        "(needs to be "
                        "###_description_ibm_db_sa_operation.sql)" % basename)
            else:
                dbms = parts[-2]
        else:
            raise exceptions.ScriptError(
                "Invalid SQL script name %s " % basename + \
                "(needs to be ###_description_database_operation.sql)")

        # File the script into a dictionary
        self.sql.setdefault(dbms, {})[op] = script.SqlScript(path)

    def _add_script_py(self, path):
        if self.python is not None:
            raise exceptions.ScriptError('You can only have one Python script '
                'per version, but you have: %s and %s' % (self.python, path))
        self.python = script.PythonScript(path)


class Extensions(object):
    """A namespace for file extensions"""
    py = 'py'
    sql = 'sql'

def str_to_filename(s):
    """Replaces spaces, (double and single) quotes
    and double underscores to underscores
    """

    s = s.replace(' ', '_').replace('"', '_').replace("'", '_').replace(".", "_")
    while '__' in s:
        s = s.replace('__', '_')
    return s
