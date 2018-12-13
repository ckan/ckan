# encoding: utf-8
from bs4 import BeautifulSoup
from nose.tools import assert_true, assert_false, assert_equal, assert_in

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers

from ckan.lib.helpers import url_for
from ckan import model
from ckan.lib.mailer import create_reset_key

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


def _get_user_edit_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for('user.edit'),
        extra_environ=env,
    )
    return env, response, user


class TestRegisterUser(helpers.FunctionalTestBase):
    def test_register_a_user(self):
        app = helpers._get_test_app()
        response = app.get(url=url_for('user.register'))

        form = response.forms['user-register-form']
        form['name'] = 'newuser'
        form['fullname'] = 'New User'
        form['email'] = 'test@test.com'
        form['password1'] = 'TestPassword1'
        form['password2'] = 'TestPassword1'
        response = submit_and_follow(app, form, name='save')
        response = response.follow()
        assert_equal(200, response.status_int)

        user = helpers.call_action('user_show', id='newuser')
        assert_equal(user['name'], 'newuser')
        assert_equal(user['fullname'], 'New User')
        assert_false(user['sysadmin'])

    def test_register_user_bad_password(self):
        app = helpers._get_test_app()
        response = app.get(url=url_for('user.register'))

        form = response.forms['user-register-form']
        form['name'] = 'newuser'
        form['fullname'] = 'New User'
        form['email'] = 'test@test.com'
        form['password1'] = 'TestPassword1'
        form['password2'] = ''

        response = form.submit('save')
        assert_true('The passwords you entered do not match' in response)

    def test_create_user_as_sysadmin(self):
        admin_pass = 'RandomPassword123'
        sysadmin = factories.Sysadmin(password=admin_pass)
        app = self._get_test_app()

        # Have to do an actual login as this test relies on repoze
        #  cookie handling.

        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]
        # fill it in
        login_form['login'] = sysadmin['name']
        login_form['password'] = admin_pass
        # submit it
        login_form.submit('save')

        response = app.get(
            url=url_for('user.register'),
        )
        assert "user-register-form" in response.forms
        form = response.forms['user-register-form']
        form['name'] = 'newestuser'
        form['fullname'] = 'Newest User'
        form['email'] = 'test@test.com'
        form['password1'] = 'NewPassword1'
        form['password2'] = 'NewPassword1'
        response2 = form.submit('save')
        assert '/user/activity' in response2.location


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
        login_form['password'] = 'RandomPassword123'

        # submit it
        submit_response = login_form.submit()
        # let's go to the last redirect in the chain
        final_response = helpers.webtest_maybe_follow(submit_response)

        # the response is the user dashboard, right?
        final_response.mustcontain('<a href="/dashboard/">Dashboard</a>',
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
        login_form['password'] = 'BadPass1'

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


class TestLogout(helpers.FunctionalTestBase):

    def test_user_logout_url_redirect(self):
        '''_logout url redirects to logged out page.

        Note: this doesn't test the actual logout of a logged in user, just
        the associated redirect.
        '''
        app = self._get_test_app()

        logout_url = url_for('user.logout')
        logout_response = app.get(logout_url, status=302)
        final_response = helpers.webtest_maybe_follow(logout_response)

        assert_true('You are now logged out.' in final_response)

    @helpers.change_config('ckan.root_path', '/my/prefix')
    def test_non_root_user_logout_url_redirect(self):
        '''
        _logout url redirects to logged out page with `ckan.root_path`
        prefixed.

        Note: this doesn't test the actual logout of a logged in user, just
        the associated redirect.
        '''
        app = self._get_test_app()

        logout_url = url_for('user.logout')
        # Remove the prefix otherwise the test app won't find the correct route
        logout_url = logout_url.replace('/my/prefix', '')
        logout_response = app.get(logout_url, status=302)
        assert_equal(logout_response.status_int, 302)
        assert_true('/my/prefix/user/logout' in logout_response.location)


class TestUser(helpers.FunctionalTestBase):

    def test_not_logged_in_dashboard(self):
        app = self._get_test_app()

        for route in ['index', 'organizations', 'datasets', 'groups']:
            app.get(
                url=url_for(u'dashboard.{}'.format(route)),
                status=403
            )

    def test_own_datasets_show_up_on_user_dashboard(self):
        user = factories.User()
        dataset_title = 'My very own dataset'
        factories.Dataset(user=user,
                          name='my-own-dataset',
                          title=dataset_title)

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for('dashboard.datasets'),
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
            url=url_for('dashboard.datasets'),
            extra_environ=env,
        )

        assert_false(dataset_title in response)


class TestUserEdit(helpers.FunctionalTestBase):

    def test_user_edit_no_user(self):
        app = self._get_test_app()
        response = app.get(
            url_for('user.edit', id=None),
            status=400
        )
        assert_true('No user specified' in response)

    def test_user_edit_unknown_user(self):
        '''Attempt to read edit user for an unknown user redirects to login
        page.'''
        app = self._get_test_app()
        response = app.get(
            url_for('user.edit', id='unknown_person'),
            status=403)

    def test_user_edit_not_logged_in(self):
        '''Attempt to read edit user for an existing, not-logged in user
        redirects to login page.'''
        app = self._get_test_app()
        user = factories.User()
        username = user['name']
        response = app.get(
            url_for('user.edit', id=username),
            status=403
        )

    def test_edit_user(self):
        user = factories.User(password='TestPassword1')
        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for('user.edit'),
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
        # form['name'] = 'new-name'
        form['fullname'] = 'new full name'
        form['email'] = 'new@example.com'
        form['about'] = 'new about'
        form['activity_streams_email_notifications'] = True
        form['old_password'] = 'TestPassword1'
        form['password1'] = 'NewPass1'
        form['password2'] = 'NewPass1'
        response = submit_and_follow(app, form, env, 'save')

        user = model.Session.query(model.User).get(user['id'])
        # assert_equal(user.name, 'new-name')
        assert_equal(user.fullname, 'new full name')
        assert_equal(user.email, 'new@example.com')
        assert_equal(user.about, 'new about')
        assert_equal(user.activity_streams_email_notifications, True)

    def test_email_change_without_password(self):

        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit-form']

        # new values
        form['email'] = 'new@example.com'

        # factory returns user with password 'pass'
        form.fields['old_password'][0].value = 'Wrong-pass1'

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('Old Password: incorrect password' in response)

    def test_email_change_with_password(self):
        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit-form']

        # new values
        form['email'] = 'new@example.com'

        # factory returns user with password 'pass'
        form.fields['old_password'][0].value = 'RandomPassword123'

        response = submit_and_follow(app, form, env, 'save')
        assert_true('Profile updated' in response)

    def test_edit_user_logged_in_username_change(self):

        user_pass = 'TestPassword1'
        user = factories.User(password=user_pass)
        app = self._get_test_app()

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]
        # fill it in
        login_form['login'] = user['name']
        login_form['password'] = user_pass
        # submit it
        login_form.submit()

        # Now the cookie is set, run the test
        response = app.get(
            url=url_for('user.edit'),
        )
        # existing values in the form
        form = response.forms['user-edit-form']

        # new values
        form['name'] = 'new-name'
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('That login name can not be modified' in response)

    def test_edit_user_logged_in_username_change_by_name(self):
        user_pass = 'TestPassword1'
        user = factories.User(password=user_pass)
        app = self._get_test_app()

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]
        # fill it in
        login_form['login'] = user['name']
        login_form['password'] = user_pass
        # submit it
        login_form.submit()

        # Now the cookie is set, run the test
        response = app.get(
            url=url_for('user.edit', id=user['name']),
        )
        # existing values in the form
        form = response.forms['user-edit-form']

        # new values
        form['name'] = 'new-name'
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('That login name can not be modified' in response)

    def test_edit_user_logged_in_username_change_by_id(self):
        user_pass = 'TestPassword1'
        user = factories.User(password=user_pass)
        app = self._get_test_app()

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.get('/user/login')
        # ...it's the second one
        login_form = response.forms[1]
        # fill it in
        login_form['login'] = user['name']
        login_form['password'] = user_pass
        # submit it
        login_form.submit()

        # Now the cookie is set, run the test
        response = app.get(
            url=url_for('user.edit', id=user['id']),
        )
        # existing values in the form
        form = response.forms['user-edit-form']

        # new values
        form['name'] = 'new-name'
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('That login name can not be modified' in response)

    def test_perform_reset_for_key_change(self):
        password = 'TestPassword1'
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

        # factory returns user with password 'RandomPassword123'
        form.fields['old_password'][0].value = 'RandomPassword123'
        form.fields['password1'][0].value = 'NewPassword1'
        form.fields['password2'][0].value = 'NewPassword1'

        response = submit_and_follow(app, form, env, 'save')
        assert_true('Profile updated' in response)

    def test_password_reset_incorrect_password(self):
        """
        user password reset attempted with invalid old password
        """

        app = self._get_test_app()
        env, response, user = _get_user_edit_page(app)

        form = response.forms['user-edit-form']

        # factory returns user with password 'RandomPassword123'
        form.fields['old_password'][0].value = 'Wrong-Pass1'
        form.fields['password1'][0].value = 'NewPassword1'
        form.fields['password2'][0].value = 'NewPassword1'

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
        response = response.follow(status=302)
        assert_in('user/login', response.headers['location'])

    def test_user_unfollow(self):
        app = self._get_test_app()

        user_one = factories.User()
        user_two = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='user',
                             action='follow',
                             id=user_two['id'])
        app.post(follow_url, extra_environ=env, status=302)

        unfollow_url = url_for('user.unfollow',
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
        unfollow_url = url_for('user.unfollow',
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
        unfollow_url = url_for('user.unfollow',
                               id='not-here')
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow(status=302)
        assert_in('user/login', unfollow_response.headers['location'])

    def test_user_follower_list(self):
        '''Following users appear on followers list page.'''
        app = self._get_test_app()

        user_one = factories.Sysadmin()
        user_two = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='user',
                             action='follow',
                             id=user_two['id'])
        app.post(follow_url, extra_environ=env, status=302)

        followers_url = url_for('user.followers',
                                id=user_two['id'])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, extra_environ=env,
                                     status=200)
        assert_true(user_one['display_name'] in followers_response)


class TestUserSearch(helpers.FunctionalTestBase):

    def test_user_page_anon_access(self):
        '''Anon users can access the user list page'''
        app = self._get_test_app()

        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200)
        assert_true('<title>All Users - CKAN</title>'
                    in user_response)

    def test_user_page_lists_users(self):
        '''/users/ lists registered users'''
        app = self._get_test_app()
        factories.User(fullname='User One')
        factories.User(fullname='User Two')
        factories.User(fullname='User Three')

        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.body)
        user_list = user_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 3)

        user_names = [u.text.strip() for u in user_list]
        assert_true('User One' in user_names)
        assert_true('User Two' in user_names)
        assert_true('User Three' in user_names)

    def test_user_page_doesnot_list_deleted_users(self):
        '''/users/ doesn't list deleted users'''
        app = self._get_test_app()
        factories.User(fullname='User One', state='deleted')
        factories.User(fullname='User Two')
        factories.User(fullname='User Three')

        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.body)
        user_list = user_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 2)

        user_names = [u.text.strip() for u in user_list]
        assert_true('User One' not in user_names)
        assert_true('User Two' in user_names)
        assert_true('User Three' in user_names)

    def test_user_page_anon_search(self):
        '''Anon users can search for users by username.'''
        app = self._get_test_app()
        factories.User(fullname='User One', email='useroneemail@example.com')
        factories.User(fullname='Person Two')
        factories.User(fullname='Person Three')

        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200)
        search_form = user_response.forms['user-search-form']
        search_form['q'] = 'Person'
        search_response = webtest_submit(search_form, status=200)

        search_response_html = BeautifulSoup(search_response.body)
        user_list = search_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 2)

        user_names = [u.text.strip() for u in user_list]
        assert_true('Person Two' in user_names)
        assert_true('Person Three' in user_names)
        assert_true('User One' not in user_names)

    def test_user_page_anon_search_not_by_email(self):
        '''Anon users can not search for users by email.'''
        app = self._get_test_app()
        factories.User(fullname='User One', email='useroneemail@example.com')
        factories.User(fullname='Person Two')
        factories.User(fullname='Person Three')

        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200)
        search_form = user_response.forms['user-search-form']
        search_form['q'] = 'useroneemail@example.com'
        search_response = webtest_submit(search_form, status=200)

        search_response_html = BeautifulSoup(search_response.body)
        user_list = search_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 0)

    def test_user_page_sysadmin_user(self):
        '''Sysadmin can search for users by email.'''
        app = self._get_test_app()
        sysadmin = factories.Sysadmin()

        factories.User(fullname='User One', email='useroneemail@example.com')
        factories.User(fullname='Person Two')
        factories.User(fullname='Person Three')

        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        user_url = url_for('user.index')
        user_response = app.get(user_url, status=200, extra_environ=env)
        search_form = user_response.forms['user-search-form']
        search_form['q'] = 'useroneemail@example.com'
        search_response = webtest_submit(search_form, status=200,
                                         extra_environ=env)

        search_response_html = BeautifulSoup(search_response.body)
        user_list = search_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 1)
        assert_equal(user_list[0].text.strip(), 'User One')
