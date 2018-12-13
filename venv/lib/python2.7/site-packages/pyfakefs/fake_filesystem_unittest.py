# Copyright 2014 Altera Corporation. All Rights Reserved.
# Copyright 2015-2017 John McGehee
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

"""This module provides a base class derived from `unittest.TestClass`
for unit tests using the :py:class:`pyfakefs` module.

`fake_filesystem_unittest.TestCase` searches `sys.modules` for modules
that import the `os`, `io`, `path` `shutil`, `pathlib`, and `tempfile`
modules.

The `setUpPyfakefs()` method binds these modules to the corresponding fake
modules from `pyfakefs`.  Further, the `open()` built-in is bound to a fake
`open()`.  In Python 2, built-in `file()` is similarly bound to the fake
`open()`.

It is expected that `setUpPyfakefs()` be invoked at the beginning of the derived
class' `setUp()` method.  There is no need to add anything to the derived
class' `tearDown()` method.

During the test, everything uses the fake file system and modules.  This means
that even in your test fixture, familiar functions like `open()` and
`os.makedirs()` manipulate the fake file system.

Existing unit tests that use the real file system can be retrofitted to use
pyfakefs by simply changing their base class from `:py:class`unittest.TestCase`
to `:py:class`pyfakefs.fake_filesystem_unittest.TestCase`.
"""

import os
import sys
import doctest
import inspect

from pyfakefs import fake_filesystem
from pyfakefs import fake_filesystem_shutil
from pyfakefs import fake_tempfile
from pyfakefs import mox3_stubout

if sys.version_info >= (3, 4):
    from pyfakefs import fake_pathlib

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

if sys.version_info < (3,):
    import __builtin__ as builtins  # pylint: disable=import-error
else:
    import builtins


def load_doctests(loader, tests, ignore, module,
                  additional_skip_names=None, patch_path=True):  # pylint: disable=unused-argument
    """Load the doctest tests for the specified module into unittest.
        Args:
            loader, tests, ignore : arguments passed in from `load_tests()`
            module: module under test 
            additional_skip_names: see :py:class:`TestCase` for an explanation
            patch_path: see :py:class:`TestCase` for an explanation

    File `example_test.py` in the pyfakefs release provides a usage example.
    """
    _patcher = Patcher(additional_skip_names=additional_skip_names,
                       patch_path=patch_path)
    globs = _patcher.replaceGlobs(vars(module))
    tests.addTests(doctest.DocTestSuite(module,
                                        globs=globs,
                                        setUp=_patcher.setUp,
                                        tearDown=_patcher.tearDown))
    return tests


class TestCase(unittest.TestCase):
    """Test case class that automatically replaces file-system related
    modules by fake implementations.
    """

    def __init__(self, methodName='runTest', additional_skip_names=None, patch_path=True):
        """Creates the test class instance and the stubber used to stub out
        file system related modules.

        Args:
            methodName: the name of the test method (same as unittest.TestCase)
            additional_skip_names: names of modules inside of which no module
                replacement shall be performed, in addition to the names in
                attribute :py:attr:`fake_filesystem_unittest.Patcher.SKIPNAMES`.
            patch_path: if False, modules named 'path' will not be patched with the
                fake 'os.path' module. Set this to False when you need to import
                some other module named 'path', for example::
                        from my_module import path
                Irrespective of patch_path, module 'os.path' is still correctly faked
                if imported the usual way using `import os` or `import os.path`.

        If you specify arguments `additional_skip_names` or `patch_path` here
        and you have DocTests, consider also specifying the same arguments to
        :py:func:`load_doctests`.
        
        Example usage in a derived test class::

          class MyTestCase(fake_filesystem_unittest.TestCase):
            def __init__(self, methodName='runTest'):
              super(MyTestCase, self).__init__(
                    methodName=methodName, additional_skip_names=['posixpath'])
        """
        super(TestCase, self).__init__(methodName)
        self._stubber = Patcher(additional_skip_names=additional_skip_names,
                                patch_path=patch_path)

    @property
    def fs(self):
        return self._stubber.fs

    @property
    def patches(self):
        return self._stubber.patches

    def copyRealFile(self, real_file_path, fake_file_path=None,
                     create_missing_dirs=True):
        """Add the file `real_file_path` in the real file system to the same
        path in the fake file system.

        **This method is deprecated** in favor of :py:meth:`FakeFilesystem..add_real_file`.
        `copyRealFile()` is retained with limited functionality for backward
        compatability only.

        Args:
          real_file_path: Path to the file in both the real and fake file systems
          fake_file_path: Deprecated.  Use the default, which is `real_file_path`.
            If a value other than `real_file_path` is specified, an `ValueError`
            exception will be raised.  
          create_missing_dirs: Deprecated.  Use the default, which creates missing
            directories in the fake file system.  If `False` is specified, an
            `ValueError` exception is raised.

        Returns:
          The newly created FakeFile object.

        Raises:
          IOError: If the file already exists in the fake file system.
          ValueError: If deprecated argument values are specified

        See:
          :py:meth:`FakeFileSystem.add_real_file`
        """
        if fake_file_path is not None and real_file_path != fake_file_path:
            raise ValueError("CopyRealFile() is deprecated and no longer supports "
                                "different real and fake file paths") 
        if not create_missing_dirs:
            raise ValueError("CopyRealFile() is deprecated and no longer supports "
                                "NOT creating missing directories")
        return self._stubber.fs.add_real_file(real_file_path, read_only=False)

    def setUpPyfakefs(self):
        """Bind the file-related modules to the :py:class:`pyfakefs` fake file
        system instead of the real file system.  Also bind the fake `open()`
        function, and on Python 2, the `file()` function.

        Invoke this at the beginning of the `setUp()` method in your unit test
        class.
        """
        self._stubber.setUp()
        self.addCleanup(self._stubber.tearDown)

    def tearDownPyfakefs(self):
        """This method is deprecated and exists only for backward compatibility.
        It does nothing.
        """
        pass


class Patcher(object):
    """
    Instantiate a stub creator to bind and un-bind the file-related modules to
    the :py:mod:`pyfakefs` fake modules.
    
    The arguments are explained in :py:class:`TestCase`.

    :py:class:`Patcher` is used in :py:class:`TestCase`.  :py:class:`Patcher`
    also works as a context manager for PyTest::
    
        with Patcher():
            doStuff()
    """
    SKIPMODULES = set([None, fake_filesystem, fake_filesystem_shutil,
                       fake_tempfile, sys])
    '''Stub nothing that is imported within these modules.
    `sys` is included to prevent `sys.path` from being stubbed with the fake
    `os.path`.
    '''
    assert None in SKIPMODULES, "sys.modules contains 'None' values; must skip them."

    HAS_PATHLIB = sys.version_info >= (3, 4)

    # To add py.test support per issue https://github.com/jmcgeheeiv/pyfakefs/issues/43,
    # it appears that adding  'py', 'pytest', '_pytest' to SKIPNAMES will help
    SKIPNAMES = set(['os', 'path', 'tempfile', 'io', 'genericpath'])
    if HAS_PATHLIB:
        SKIPNAMES.add('pathlib')

    def __init__(self, additional_skip_names=None, patch_path=True):
        """For a description of the arguments, see TestCase.__init__"""

        self._skipNames = self.SKIPNAMES.copy()
        if additional_skip_names is not None:
            self._skipNames.update(additional_skip_names)
        self._patchPath = patch_path
        if not patch_path:
            self._skipNames.discard('path')
            self._skipNames.discard('genericpath')

        # Attributes set by _findModules()
        self._os_modules = None
        self._path_modules = None
        if self.HAS_PATHLIB:
            self._pathlib_modules = None
        self._shutil_modules = None
        self._tempfile_modules = None
        self._io_modules = None
        self._findModules()
        assert None not in vars(self).values(), \
            "_findModules() missed the initialization of an instance variable"

        # Attributes set by _refresh()
        self._stubs = None
        self.fs = None
        self.fake_os = None
        self.fake_path = None
        if self.HAS_PATHLIB:
            self.fake_pathlib = None
        self.fake_shutil = None
        self.fake_tempfile_ = None
        self.fake_open = None
        self.fake_io = None
        # _isStale is set by tearDown(), reset by _refresh()
        self._isStale = True
        self._refresh()
        assert None not in vars(self).values(), \
            "_refresh() missed the initialization of an instance variable"
        assert self._isStale == False, "_refresh() did not reset _isStale"

    def __enter__(self):
        """Context manager for usage outside of fake_filesystem_unittest.TestCase.
        Ensure that all patched modules are removed in case of an unhandled exception.
        """
        self.setUp()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tearDown()

    def _findModules(self):
        """Find and cache all modules that import file system modules.
        Later, `setUp()` will stub these with the fake file system
        modules.
        """
        self._os_modules = set()
        self._path_modules = set()
        if self.HAS_PATHLIB:
            self._pathlib_modules = set()
        self._shutil_modules = set()
        self._tempfile_modules = set()
        self._io_modules = set()
        for name, module in set(sys.modules.items()):
            if (module in self.SKIPMODULES or
                    (not inspect.ismodule(module)) or
                        name.split('.')[0] in self._skipNames):
                continue
            # IMPORTANT TESTING NOTE: Whenever you add a new module below, test
            # it by adding an attribute in fixtures/module_with_attributes.py
            # and a test in fake_filesystem_unittest_test.py, class
            # TestAttributesWithFakeModuleNames.
            if inspect.ismodule(module.__dict__.get('os')):
                self._os_modules.add(module)
            if self._patchPath and inspect.ismodule(module.__dict__.get('path')):
                self._path_modules.add(module)
            if self.HAS_PATHLIB and inspect.ismodule(module.__dict__.get('pathlib')):
                self._pathlib_modules.add(module)
            if inspect.ismodule(module.__dict__.get('shutil')):
                self._shutil_modules.add(module)
            if inspect.ismodule(module.__dict__.get('tempfile')):
                self._tempfile_modules.add(module)
            if inspect.ismodule(module.__dict__.get('io')):
                self._io_modules.add(module)

    def _refresh(self):
        """Renew the fake file system and set the _isStale flag to `False`."""
        if self._stubs is not None:
            self._stubs.SmartUnsetAll()
        self._stubs = mox3_stubout.StubOutForTesting()

        self.fs = fake_filesystem.FakeFilesystem()
        self.fake_os = fake_filesystem.FakeOsModule(self.fs)
        self.fake_path = self.fake_os.path
        if self.HAS_PATHLIB:
            self.fake_pathlib = fake_pathlib.FakePathlibModule(self.fs)
        self.fake_shutil = fake_filesystem_shutil.FakeShutilModule(self.fs)
        self.fake_tempfile_ = fake_tempfile.FakeTempfileModule(self.fs)
        self.fake_open = fake_filesystem.FakeFileOpen(self.fs)
        self.fake_io = fake_filesystem.FakeIoModule(self.fs)

        self._isStale = False

    def setUp(self, doctester=None):
        """Bind the file-related modules to the :py:mod:`pyfakefs` fake
        modules real ones.  Also bind the fake `file()` and `open()` functions.
        """
        self._refresh()

        if doctester is not None:
            doctester.globs = self.replaceGlobs(doctester.globs)

        if sys.version_info < (3,):
            # file() was eliminated in Python3
            self._stubs.SmartSet(builtins, 'file', self.fake_open)
        self._stubs.SmartSet(builtins, 'open', self.fake_open)

        for module in self._os_modules:
            self._stubs.SmartSet(module, 'os', self.fake_os)
        for module in self._path_modules:
            self._stubs.SmartSet(module, 'path', self.fake_path)
        if self.HAS_PATHLIB:
            for module in self._pathlib_modules:
                self._stubs.SmartSet(module, 'pathlib', self.fake_pathlib)
        for module in self._shutil_modules:
            self._stubs.SmartSet(module, 'shutil', self.fake_shutil)
        for module in self._tempfile_modules:
            self._stubs.SmartSet(module, 'tempfile', self.fake_tempfile_)
        for module in self._io_modules:
            self._stubs.SmartSet(module, 'io', self.fake_io)

    def replaceGlobs(self, globs_):
        globs = globs_.copy()
        if self._isStale:
            self._refresh()
        if 'os' in globs:
            globs['os'] = fake_filesystem.FakeOsModule(self.fs)
        if 'path' in globs:
            fake_os = globs['os'] if 'os' in globs \
                else fake_filesystem.FakeOsModule(self.fs)
            globs['path'] = fake_os.path
        if 'shutil' in globs:
            globs['shutil'] = fake_filesystem_shutil.FakeShutilModule(self.fs)
        if 'tempfile' in globs:
            globs['tempfile'] = fake_tempfile.FakeTempfileModule(self.fs)
        if 'io' in globs:
            globs['io'] = fake_filesystem.FakeIoModule(self.fs)
        return globs

    def tearDown(self, doctester=None):
        """Clear the fake filesystem bindings created by `setUp()`."""
        self._isStale = True
        self._stubs.SmartUnsetAll()
