import warnings

warnings.warn(
    "ckan.tests has been renamed to ckan.tests_legacy. "
    "In the next release it is planned to remove ckan.tests, and possibly "
    "rename ckan.new_tests to ckan.tests.",
    FutureWarning)

from ckan.tests_legacy.functional.base import *
