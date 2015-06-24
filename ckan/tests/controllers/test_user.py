from nose.tools import assert_true, assert_false, assert_equal

from routes import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan import model
from ckan.lib.mailer import create_reset_key


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
        user = factories.User(password='pass')
        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='user', action='edit'),
            extra_environ=env,
        )
        # existing values in the form
        form = response.forms['user-edit-form']
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
        form['old_password'] = 'pass'
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

    def test_password_reset_correct_password(self):
        """
        user password reset attempted with correct old password
        """
        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit-form']

        # factory returns user with password 'pass'
        form.fields['old_password'][0].value = 'pass'
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

        form = response.forms['user-edit-form']

        # factory returns user with password 'pass'
        form.fields['old_password'][0].value = 'wrong-pass'
        form.fields['password1'][0].value = 'newpass'
        form.fields['password2'][0].value = 'newpass'

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('Old Password: incorrect password' in response)


class TestUserFollow(helpers.FunctionalTestBase):

    def test_user_follow(self):
        app = self._get_test_app()

        user_one = factories.User()
        user_two = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='user',
                             action='follow',
                             id=user_two['id'])
        response = app.post(follow_url, extra_environ=env, status=302)
        response = response.follow()
        assert_true('You are now following {0}'
                    .format(user_two['display_name'])
                    in response)

    def test_user_follow_not_exist(self):
        '''Pass an id for a user that doesn't exist'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='user',
                             action='follow',
                             id='not-here')
        response = app.post(follow_url, extra_environ=env, status=302)
        response = response.follow(status=404)
        assert_true('User not found' in response)

    def test_user_unfollow(self):
        app = self._get_test_app()

        user_one = factories.User()
        user_two = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='user',
                             action='follow',
                             id=user_two['id'])
        app.post(follow_url, extra_environ=env, status=302)

        unfollow_url = url_for(controller='user', action='unfollow',
                               id=user_two['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are no longer following {0}'
                    .format(user_two['display_name'])
                    in unfollow_response)

    def test_user_unfollow_not_following(self):
        '''Unfollow a user not currently following'''
        app = self._get_test_app()

        user_one = factories.User()
        user_two = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='user', action='unfollow',
                               id=user_two['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are not following {0}'.format(user_two['id'])
                    in unfollow_response)

    def test_user_unfollow_not_exist(self):
        '''Unfollow a user that doesn't exist.'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='user', action='unfollow',
                               id='not-here')
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow(status=404)

        assert_true('User not found' in unfollow_response)
