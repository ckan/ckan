# encoding: utf-8
import warnings

from ckan.plugins.core import *  # noqa: re-export
from ckan.plugins.interfaces import *  # noqa: re-export


def __getattr__(name):
    if name == 'toolkit':
        import ckan.plugins.toolkit as t
        from ckan.exceptions import CkanDeprecationWarning
        msg = ("`toolkit` attribute of the `ckan.plugins` module will be"
               "removed in future CKAN release. Import `ckan.plugins.toolkit`"
               " directly instead:\n\t"
               "import ckan.plugins.toolkit as toolkit")
        warnings.warn(
            msg, CkanDeprecationWarning, stacklevel=2
        )

        return t
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
