from nose.tools import assert_equal, assert_true

from routes import url_for

from ckan.new_tests.controllers import WsgiAppCase
from ckan.new_tests.factories import Sysadmin


class TestPackageController(WsgiAppCase):
    def test_create_form_renders(self):
        user = Sysadmin()
        extra_environ = {
            'REMOTE_USER': user['name'].encode('ascii'),
        }
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=extra_environ,
        )
        assert_true('dataset-edit' in response.forms)
