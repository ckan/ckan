# FIXME: remove this for ckan 2.5
import sys


class _NewTestsBackwardsCompat(object):
    """
    Provide (temporarily) backward compatibility for extensions that
    pre-date the move of tests from ckan.new_tests to ckan.tests.
    """

    # things our object-pretending-to-be-a-module need:
    __name__ = __name__

    def __getattr__(self, name):
        import ckan.tests
        import logging
        value = getattr(ckan.tests, name)
        log = logging.getLogger('ckan.tests')
        log.warn(
            "ckan.new_tests has been renamed to ckan.tests."
            "In the next release tests will only be available "
            "from ckan.tests.")
        return value

# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = _NewTestsBackwardsCompat()
