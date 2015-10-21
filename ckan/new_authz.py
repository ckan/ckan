import warnings

warnings.warn(
    "ckan.new_authz has been renamed to ckan.authz. "
    "The ckan.new_authz module will be removed in a future release.",
    FutureWarning)

from ckan.authz import *
