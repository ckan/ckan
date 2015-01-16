import warnings

warnings.warn(
    "ckan.tests has been renamed to ckan.tests.legacy. "
    "In the next release it is planned to remove ckan.tests, and possibly "
    "rename ckan.new_tests to ckan.tests.",
    FutureWarning)

from ckan.tests.legacy.functional.api.base import *
