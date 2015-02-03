from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.new_tests.helpers as helpers
from ckan.new_tests import factories

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


def _get_user_edit_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='user', action='edit'),
        extra_environ=env,
    )
    return env, response, user


class TestUserControllerEdit(helpers.FunctionalTestBase):
    def test_password_reset_correct_password(self):
        """
        user password reset attempted with correct old password
        """
        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit']

        # factory returns user with password 'pass'
        form.fields['old-password'][0].value = 'pass'
        form.fields['password1'][0].value = 'newpass'
        form.fields['password2'][0].value = 'newpass'

        response = submit_and_follow(app, form, env, 'save')
        assert_true('Profile updated' in response)

    def test_password_reset_incorrect_password(self):
        """
        user password reset attempted with invalid old password
        """

        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit']

        # factory returns user with password 'pass'
        form.fields['old-password'][0].value = 'wrong-pass'
        form.fields['password1'][0].value = 'newpass'
        form.fields['password2'][0].value = 'newpass'

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('Old Password: incorrect password' in response)