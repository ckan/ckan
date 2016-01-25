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


try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict


class CKANConfig(dict):

    pylons_config = None
    flask_config = None

    def __init__(self, *arg, **kw):
        super(CKANConfig, self).__init__(*arg, **kw)

    def initialize(self, pylons_config=None, flask_config=None):

        self.pylons_config = pylons_config
        self.flask_config = flask_config

    def __setitem__(self, key, value):

        super(CKANConfig, self).__setitem__(key, value)
        if self.pylons_config:
            self.pylons_config[key] = value
        if self.flask_config:
            self.flask_config[key] = value

    def _delitem__(self, key):

        super(CKANConfig, self).__delitem__(key)
        if self.pylons_config:
            del self.pylons_config[key]
        if self.flask_app:
            del self.flask_app.config[key]

# Will be initialized on environment.load_environment
#config = {}
config = CKANConfig()
