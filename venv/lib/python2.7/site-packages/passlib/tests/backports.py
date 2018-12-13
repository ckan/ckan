"""backports of needed unittest2 features"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
import logging; log = logging.getLogger(__name__)
import re
import sys
##from warnings import warn
# site
# pkg
from passlib.utils.compat import base_string_types
# local
__all__ = [
    "TestCase",
    "skip", "skipIf", "skipUnless"
    "catch_warnings",
]

#=============================================================================
# import latest unittest module available
#=============================================================================
try:
    import unittest2 as unittest
    ut_version = 2
except ImportError:
    import unittest
    if sys.version_info < (2,7) or (3,0) <= sys.version_info < (3,2):
        # older versions of python will need to install the unittest2
        # backport (named unittest2_3k for 3.0/3.1)
        ##warn("please install unittest2 for python %d.%d, it will be required "
        ##     "as of passlib 1.x" % sys.version_info[:2])
        ut_version = 1
    else:
        ut_version = 2

#=============================================================================
# backport SkipTest support using nose
#=============================================================================
if ut_version < 2:
    # used to provide replacement SkipTest() error
    from nose.plugins.skip import SkipTest

    # hack up something to simulate skip() decorator
    import functools
    def skip(reason):
        def decorator(test_item):
            if isinstance(test_item, type) and issubclass(test_item, unittest.TestCase):
                class skip_wrapper(test_item):
                    def setUp(self):
                        raise SkipTest(reason)
            else:
                @functools.wraps(test_item)
                def skip_wrapper(*args, **kwargs):
                    raise SkipTest(reason)
            return skip_wrapper
        return decorator

    def skipIf(condition, reason):
        if condition:
            return skip(reason)
        else:
            return lambda item: item

    def skipUnless(condition, reason):
        if condition:
            return lambda item: item
        else:
            return skip(reason)

else:
    skip = unittest.skip
    skipIf = unittest.skipIf
    skipUnless = unittest.skipUnless

#=============================================================================
# custom test harness
#=============================================================================
class TestCase(unittest.TestCase):
    """backports a number of unittest2 features in TestCase"""
    #===================================================================
    # backport some methods from unittest2
    #===================================================================
    if ut_version < 2:

        #----------------------------------------------------------------
        # simplistic backport of addCleanup() framework
        #----------------------------------------------------------------
        _cleanups = None

        def addCleanup(self, function, *args, **kwds):
            queue = self._cleanups
            if queue is None:
                queue = self._cleanups = []
            queue.append((function, args, kwds))

        def doCleanups(self):
            queue = self._cleanups
            while queue:
                func, args, kwds = queue.pop()
                func(*args, **kwds)

        def tearDown(self):
            self.doCleanups()
            unittest.TestCase.tearDown(self)

        #----------------------------------------------------------------
        # backport skipTest (requires nose to work)
        #----------------------------------------------------------------
        def skipTest(self, reason):
            raise SkipTest(reason)

        #----------------------------------------------------------------
        # backport various assert tests added in unittest2
        #----------------------------------------------------------------
        def assertIs(self, real, correct, msg=None):
            if real is not correct:
                std = "got %r, expected would be %r" % (real, correct)
                msg = self._formatMessage(msg, std)
                raise self.failureException(msg)

        def assertIsNot(self, real, correct, msg=None):
            if real is correct:
                std = "got %r, expected would not be %r" % (real, correct)
                msg = self._formatMessage(msg, std)
                raise self.failureException(msg)

        def assertIsInstance(self, obj, klass, msg=None):
            if not isinstance(obj, klass):
                std = "got %r, expected instance of %r" % (obj, klass)
                msg = self._formatMessage(msg, std)
                raise self.failureException(msg)

        def assertAlmostEqual(self, first, second, places=None, msg=None, delta=None):
            """Fail if the two objects are unequal as determined by their
               difference rounded to the given number of decimal places
               (default 7) and comparing to zero, or by comparing that the
               between the two objects is more than the given delta.

               Note that decimal places (from zero) are usually not the same
               as significant digits (measured from the most signficant digit).

               If the two objects compare equal then they will automatically
               compare almost equal.
            """
            if first == second:
                # shortcut
                return
            if delta is not None and places is not None:
                raise TypeError("specify delta or places not both")

            if delta is not None:
                if abs(first - second) <= delta:
                    return

                standardMsg = '%s != %s within %s delta' % (repr(first),
                                                            repr(second),
                                                            repr(delta))
            else:
                if places is None:
                    places = 7

                if round(abs(second-first), places) == 0:
                    return

                standardMsg = '%s != %s within %r places' % (repr(first),
                                                              repr(second),
                                                              places)
            msg = self._formatMessage(msg, standardMsg)
            raise self.failureException(msg)

        def assertLess(self, left, right, msg=None):
            if left >= right:
                std = "%r not less than %r" % (left, right)
                raise self.failureException(self._formatMessage(msg, std))

        def assertGreater(self, left, right, msg=None):
            if left <= right:
                std = "%r not greater than %r" % (left, right)
                raise self.failureException(self._formatMessage(msg, std))

        def assertGreaterEqual(self, left, right, msg=None):
            if left < right:
                std = "%r less than %r" % (left, right)
                raise self.failureException(self._formatMessage(msg, std))

        def assertIn(self, elem, container, msg=None):
            if elem not in container:
                std = "%r not found in %r" % (elem, container)
                raise self.failureException(self._formatMessage(msg, std))

        def assertNotIn(self, elem, container, msg=None):
            if elem in container:
                std = "%r unexpectedly in %r" % (elem, container)
                raise self.failureException(self._formatMessage(msg, std))

        #----------------------------------------------------------------
        # override some unittest1 methods to support _formatMessage
        #----------------------------------------------------------------
        def assertEqual(self, real, correct, msg=None):
            if real != correct:
                std = "got %r, expected would equal %r" % (real, correct)
                msg = self._formatMessage(msg, std)
                raise self.failureException(msg)

        def assertNotEqual(self, real, correct, msg=None):
            if real == correct:
                std = "got %r, expected would not equal %r" % (real, correct)
                msg = self._formatMessage(msg, std)
                raise self.failureException(msg)

    #---------------------------------------------------------------
    # backport assertRegex() alias from 3.2 to 2.7/3.1
    #---------------------------------------------------------------
    if not hasattr(unittest.TestCase, "assertRegex"):
        if hasattr(unittest.TestCase, "assertRegexpMatches"):
            # was present in 2.7/3.1 under name assertRegexpMatches
            assertRegex = unittest.TestCase.assertRegexpMatches
        else:
            # 3.0 and <= 2.6 didn't have this method at all
            def assertRegex(self, text, expected_regex, msg=None):
                """Fail the test unless the text matches the regular expression."""
                if isinstance(expected_regex, base_string_types):
                    assert expected_regex, "expected_regex must not be empty."
                    expected_regex = re.compile(expected_regex)
                if not expected_regex.search(text):
                    msg = msg or "Regex didn't match: "
                    std = '%r not found in %r' % (msg, expected_regex.pattern, text)
                    raise self.failureException(self._formatMessage(msg, std))

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# backport catch_warnings
#=============================================================================
try:
    from warnings import catch_warnings
except ImportError:
    # catch_warnings wasn't added until py26.
    # this adds backported copy from py26's stdlib
    # so we can use it under py25.

    class WarningMessage(object):

        """Holds the result of a single showwarning() call."""

        _WARNING_DETAILS = ("message", "category", "filename", "lineno", "file",
                            "line")

        def __init__(self, message, category, filename, lineno, file=None,
                        line=None):
            local_values = locals()
            for attr in self._WARNING_DETAILS:
                setattr(self, attr, local_values[attr])
            self._category_name = category.__name__ if category else None

        def __str__(self):
            return ("{message : %r, category : %r, filename : %r, lineno : %s, "
                        "line : %r}" % (self.message, self._category_name,
                                        self.filename, self.lineno, self.line))


    class catch_warnings(object):

        """A context manager that copies and restores the warnings filter upon
        exiting the context.

        The 'record' argument specifies whether warnings should be captured by a
        custom implementation of warnings.showwarning() and be appended to a list
        returned by the context manager. Otherwise None is returned by the context
        manager. The objects appended to the list are arguments whose attributes
        mirror the arguments to showwarning().

        The 'module' argument is to specify an alternative module to the module
        named 'warnings' and imported under that name. This argument is only useful
        when testing the warnings module itself.

        """

        def __init__(self, record=False, module=None):
            """Specify whether to record warnings and if an alternative module
            should be used other than sys.modules['warnings'].

            For compatibility with Python 3.0, please consider all arguments to be
            keyword-only.

            """
            self._record = record
            self._module = sys.modules['warnings'] if module is None else module
            self._entered = False

        def __repr__(self):
            args = []
            if self._record:
                args.append("record=True")
            if self._module is not sys.modules['warnings']:
                args.append("module=%r" % self._module)
            name = type(self).__name__
            return "%s(%s)" % (name, ", ".join(args))

        def __enter__(self):
            if self._entered:
                raise RuntimeError("Cannot enter %r twice" % self)
            self._entered = True
            self._filters = self._module.filters
            self._module.filters = self._filters[:]
            self._showwarning = self._module.showwarning
            if self._record:
                log = []
                def showwarning(*args, **kwargs):
#                    self._showwarning(*args, **kwargs)
                    log.append(WarningMessage(*args, **kwargs))
                self._module.showwarning = showwarning
                return log
            else:
                return None

        def __exit__(self, *exc_info):
            if not self._entered:
                raise RuntimeError("Cannot exit %r without entering first" % self)
            self._module.filters = self._filters
            self._module.showwarning = self._showwarning

#=============================================================================
# eof
#=============================================================================
