from nose.tools import assert_true, assert_false

from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
from ckan.lib.mailer import create_reset_key


class TestPackageControllerNew(helpers.FunctionalTestBase):

    def test_perform_reset_for_key_change(self):
        password = 'password'
        params = {'password1': password, 'password2': password}
        user = factories.User()
        user_obj = helpers.model.User.by_name(user['name'])
        create_reset_key(user_obj)
        key = user_obj.reset_key

        app = self._get_test_app()
        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user_obj.id,
                         key=user_obj.reset_key)
        response = app.post(offset, params=params, status=302)
        user_obj = helpers.model.User.by_name(user['name'])  # Update user_obj

        assert_true(key != user_obj.reset_key)
