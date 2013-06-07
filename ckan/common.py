# This file contains commonly used parts of external libraries. The idea is
# to help in removing helpers from being used as a dependency by many files
# but at the same time making it easy to change for example the json lib
# used.
#
# NOTE:  This file is specificaly created for
# from ckan.common import x, y, z to be allowed


from pylons.i18n import _, ungettext
from pylons import g, c, request, session, response
import simplejson as json

# importing a part of ckan here is bad as we risk recreating circular import
# issues.  However the config is quite nice to be easily accessed and is
# quite self contained code
import ckan.lib.config_obj as _config_obj
ckan_config = _config_obj.ckan_config
del _config_obj

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict
