from nose.tools import assert_true, assert_false, assert_equal

from routes import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan import model
from ckan.lib.mailer import create_reset_key


submit_and_follow = helpers.submit_and_follow


class TestUser(helpers.FunctionalTestBase):

    def test_own_datasets_show_up_on_user_dashboard(self):
        user = factories.User()
        dataset_title = 'My very own dataset'
        factories.Dataset(user=user,
                          name='my-own-dataset',
                          title=dataset_title)

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='user', action='dashboard_datasets'),
            extra_environ=env,
        )

        assert_true(dataset_title in response)

    def test_other_datasets_dont_show_up_on_user_dashboard(self):
        user1 = factories.User()
        user2 = factories.User()
        dataset_title = 'Someone else\'s dataset'
        factories.Dataset(user=user1,
                          name='someone-elses-dataset',
                          title=dataset_title)

        app = self._get_test_app()
        env = {'REMOTE_USER': user2['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='user', action='dashboard_datasets'),
            extra_environ=env,
        )

        assert_false(dataset_title in response)

    def test_edit_user(self):
        user = factories.User()
        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='user', action='edit'),
            extra_environ=env,
        )
        # existing values in the form
        form = response.forms['user-edit']
        assert_equal(form['name'].value, user['name'])
        assert_equal(form['fullname'].value, user['fullname'])
        assert_equal(form['email'].value, user['email'])
        assert_equal(form['about'].value, user['about'])
        assert_equal(form['activity_streams_email_notifications'].value, None)
        assert_equal(form['password1'].value, '')
        assert_equal(form['password2'].value, '')

        # new values
        #form['name'] = 'new-name'
        form['fullname'] = 'new full name'
        form['email'] = 'new@example.com'
        form['about'] = 'new about'
        form['activity_streams_email_notifications'] = True
        form['password1'] = 'newpass'
        form['password2'] = 'newpass'
        response = submit_and_follow(app, form, env, 'save')

        user = model.Session.query(model.User).get(user['id'])
        #assert_equal(user.name, 'new-name')
        assert_equal(user.fullname, 'new full name')
        assert_equal(user.email, 'new@example.com')
        assert_equal(user.about, 'new about')
        assert_equal(user.activity_streams_email_notifications, True)

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
