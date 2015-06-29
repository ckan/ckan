from bs4 import BeautifulSoup
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


class TestUserSearch(helpers.FunctionalTestBase):

    def test_user_page_anon_access(self):
        '''Anon users can access the user list page'''
        app = self._get_test_app()

        user_url = url_for(controller='user', action='index')
        user_response = app.get(user_url, status=200)
        assert_true('<title>All Users - CKAN</title>'
                    in user_response)

    def test_user_page_lists_users(self):
        '''/users/ lists registered users'''
        app = self._get_test_app()
        factories.User(fullname='User One')
        factories.User(fullname='User Two')
        factories.User(fullname='User Three')

        user_url = url_for(controller='user', action='index')
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.body)
        user_list = user_response_html.select('ul.user-list li')
        # two pseudo users + the users we've added
        assert_equal(len(user_list), 2 + 3)

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

        user_url = url_for(controller='user', action='index')
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.body)
        user_list = user_response_html.select('ul.user-list li')
        # two pseudo users + the users we've added
        assert_equal(len(user_list), 2 + 2)

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

        user_url = url_for(controller='user', action='index')
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

        user_url = url_for(controller='user', action='index')
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
        user_url = url_for(controller='user', action='index')
        user_response = app.get(user_url, status=200, extra_environ=env)
        search_form = user_response.forms['user-search-form']
        search_form['q'] = 'useroneemail@example.com'
        search_response = webtest_submit(search_form, status=200,
                                         extra_environ=env)

        search_response_html = BeautifulSoup(search_response.body)
        user_list = search_response_html.select('ul.user-list li')
        assert_equal(len(user_list), 1)
        assert_equal(user_list[0].text.strip(), 'User One')
