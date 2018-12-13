#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import tempfile

from migrate.tests.fixture import base


class Pathed(base.Base):
    # Temporary files

    _tmpdir = tempfile.mkdtemp()

    def setUp(self):
        super(Pathed, self).setUp()
        self.temp_usable_dir = tempfile.mkdtemp()
        sys.path.append(self.temp_usable_dir)

    def tearDown(self):
        super(Pathed, self).tearDown()
        try:
            sys.path.remove(self.temp_usable_dir)
        except:
            pass # w00t?
        Pathed.purge(self.temp_usable_dir)

    @classmethod
    def _tmp(cls, prefix='', suffix=''):
        """Generate a temporary file name that doesn't exist
        All filenames are generated inside a temporary directory created by
        tempfile.mkdtemp(); only the creating user has access to this directory.
        It should be secure to return a nonexistant temp filename in this
        directory, unless the user is messing with their own files.
        """
        file, ret = tempfile.mkstemp(suffix,prefix,cls._tmpdir)
        os.close(file)
        os.remove(ret)
        return ret

    @classmethod
    def tmp(cls, *p, **k):
        return cls._tmp(*p, **k)

    @classmethod
    def tmp_py(cls, *p, **k):
        return cls._tmp(suffix='.py', *p, **k)

    @classmethod
    def tmp_sql(cls, *p, **k):
        return cls._tmp(suffix='.sql', *p, **k)

    @classmethod
    def tmp_named(cls, name):
        return os.path.join(cls._tmpdir, name)

    @classmethod
    def tmp_repos(cls, *p, **k):
        return cls._tmp(*p, **k)

    @classmethod
    def purge(cls, path):
        """Removes this path if it exists, in preparation for tests
        Careful - all tests should take place in /tmp.
        We don't want to accidentally wipe stuff out...
        """
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                if path.endswith('.py'):
                    pyc = path + 'c'
                    if os.path.exists(pyc):
                        os.remove(pyc)
