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


class TestRegisterUser(helpers.FunctionalTestBase):
    def test_register_a_user(self):
        app = helpers._get_test_app()
        response = app.get(url=url_for(controller='user', action='register'))

        form = response.forms['user-register-form']
        form['name'] = 'newuser'
        form['fullname'] = 'New User'
        form['email'] = 'test@test.com'
        form['password1'] = 'testpassword'
        form['password2'] = 'testpassword'
        response = submit_and_follow(app, form, name='save')
        response = response.follow()
        assert_equal(200, response.status_int)

        user = helpers.call_action('user_show', id='newuser')
        assert_equal(user['name'], 'newuser')
        assert_equal(user['fullname'], 'New User')
        assert_false(user['sysadmin'])

    def test_register_user_bad_password(self):
        app = helpers._get_test_app()
        response = app.get(url=url_for(controller='user', action='register'))

        form = response.forms['user-register-form']
        form['name'] = 'newuser'
        form['fullname'] = 'New User'
        form['email'] = 'test@test.com'
        form['password1'] = 'testpassword'
        form['password2'] = ''

        response = form.submit('save')
        assert_true('The passwords you entered do not match')


class TestLoginView(helpers.FunctionalTestBase):
    def test_registered_user_login(self):
        '''
        Registered user can submit valid login details at /user/login and
        be returned to appropriate place.
        '''
        app = helpers._get_test_app()

        # make a user
        user = factories.User()

        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]

        # fill it in
        login_form['login'] = user['name']
        login_form['password'] = 'pass'

        # submit it
        submit_response = login_form.submit()
        # let's go to the last redirect in the chain
        final_response = helpers.webtest_maybe_follow(submit_response)

        # the response is the user dashboard, right?
        final_response.mustcontain('<a href="/dashboard">Dashboard</a>',
                                   '<span class="username">{0}</span>'
                                   .format(user['fullname']))
        # and we're definitely not back on the login page.
        final_response.mustcontain(no='<h1 class="page-heading">Login</h1>')

    def test_registered_user_login_bad_password(self):
        '''
        Registered user is redirected to appropriate place if they submit
        invalid login details at /user/login.
        '''
        app = helpers._get_test_app()

        # make a user
        user = factories.User()

        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]

        # fill it in
        login_form['login'] = user['name']
        login_form['password'] = 'badpass'

        # submit it
        submit_response = login_form.submit()
        # let's go to the last redirect in the chain
        final_response = helpers.webtest_maybe_follow(submit_response)

        # the response is the login page again
        final_response.mustcontain('<h1 class="page-heading">Login</h1>',
                                   'Login failed. Bad username or password.')
        # and we're definitely not on the dashboard.
        final_response.mustcontain(no='<a href="/dashboard">Dashboard</a>'),
        final_response.mustcontain(no='<span class="username">{0}</span>'
                                   .format(user['fullname']))


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
