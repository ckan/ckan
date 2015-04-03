# FIXME: remove everything in this file for ckan 2.5
import sys


class _LegacyTestsBackwardsCompat(object):
    """
    Import provides (temporarily) backward compatibility for extensions that
    pre-date the move of tests from ckan.tests to ckan.test.legacy.
    """

    # things our object-pretending-to-be-a-module need:
    __path__ = __path__
    __name__ = __name__

    def __getattr__(self, name):
        import ckan.tests.legacy
        import logging
        value = getattr(ckan.tests.legacy, name)
        log = logging.getLogger('ckan.tests')
        log.warn(
            "ckan.tests has been renamed to ckan.tests.legacy."
            "In the next release legacy tests will only be available "
            "from ckan.tests.legacy.")
        return value

# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = _LegacyTestsBackwardsCompat()
