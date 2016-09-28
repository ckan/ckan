# encoding: utf-8

from ckan.lib.helpers import url_for
from nose.tools import assert_equal
from ckan.common import config
import hashlib

from ckan.tests.legacy import CreateTestData
from ckan.tests.legacy.html_check import HtmlCheckMethods
from ckan.tests.legacy.pylons_controller import PylonsTestCase
from ckan.tests.legacy.mock_mail_server import SmtpServerHarness
import ckan.model as model
from base import FunctionalTestCase
from ckan.lib.mailer import get_reset_link, create_reset_key

class TestUserController(FunctionalTestCase, HtmlCheckMethods, PylonsTestCase, SmtpServerHarness):
    @classmethod
    def setup_class(cls):
        smtp_server = config.get('smtp.test_server')
        if smtp_server:
            host, port = smtp_server.split(':')
            port = int(port) + int(str(hashlib.md5(cls.__name__).hexdigest())[0], 16)
            config['smtp.test_server'] = '%s:%s' % (host, port)

        PylonsTestCase.setup_class()
        SmtpServerHarness.setup_class()
        CreateTestData.create()

        # make 3 changes, authored by annafan
        for i in range(3):
            rev = model.repo.new_revision()
            pkg = model.Package.by_name(u'annakarenina')
            pkg.notes = u'Changed notes %i' % i
            rev.author = u'annafan'
            model.repo.commit_and_remove()

        CreateTestData.create_user('unfinisher', about='<a href="http://unfinished.tag')
        CreateTestData.create_user('uncloser', about='<a href="http://unclosed.tag">')
        CreateTestData.create_user('spammer', about=u'<a href="http://mysite">mysite</a> <a href=\u201dhttp://test2\u201d>test2</a>')
        CreateTestData.create_user('spammer2', about=u'<a href="http://spamsite1.com\u201d>spamsite1</a>\r\n<a href="http://www.spamsite2.com\u201d>spamsite2</a>\r\n')

    @classmethod
    def teardown_class(self):
        # clear routes 'id' so that next test to run doesn't get it
        self.app.get(url_for(controller='user', action='login', id=None))
        SmtpServerHarness.teardown_class()
        model.repo.rebuild_db()

    def teardown(self):
        # just ensure we're not logged in
        self.app.get('/user/logout')

    def test_user_delete_redirects_to_user_index(self):
        user = CreateTestData.create_user('a_user')
        url = url_for(controller='user', action='delete', id=user.id)
        extra_environ = {'REMOTE_USER': 'testsysadmin'}

        redirect_url = url_for(controller='user', action='index',
                qualified=True)
        res = self.app.get(url, status=302, extra_environ=extra_environ)

        assert user.is_deleted(), user
        assert res.header('Location').startswith(redirect_url), res.header('Location')

    def test_user_delete_by_unauthorized_user(self):
        user = model.User.by_name(u'annafan')
        url = url_for(controller='user', action='delete', id=user.id)
        extra_environ = {'REMOTE_USER': 'an_unauthorized_user'}

        self.app.get(url, status=403, extra_environ=extra_environ)

    def test_user_read_without_id(self):
        offset = '/user/'
        res = self.app.get(offset, status=302)

    def test_user_read_me_without_id(self):
        offset = '/user/me'
        res = self.app.get(offset, status=302)

    def _get_cookie_headers(self, res):
        # For a request response, returns the Set-Cookie header values.
        cookie_headers = []
        for key, value in res.headers:
            if key == 'Set-Cookie':
                cookie_headers.append(value)
        return cookie_headers

    def test_apikey(self):
        username= u'okfntest'
        user = model.User.by_name(u'okfntest')
        if not user:
            user = model.User(name=u'okfntest')
            model.Session.add(user)
            model.Session.commit()
            model.Session.remove()

        # not logged in
        offset = url_for(controller='user', action='read', id=username)
        res = self.app.get(offset)
        assert not 'API key' in res

        offset = url_for(controller='user', action='read', id='okfntest')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'okfntest'})
        assert user.apikey in res, res

    def test_perform_reset_user_password_link_key_incorrect(self):
        CreateTestData.create_user(name='jack', password='test1')
        # Make up a key - i.e. trying to hack this
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id,
                         key='randomness') # i.e. incorrect
        res = self.app.get(offset, status=403) # error

    def test_perform_reset_user_password_link_key_missing(self):
        CreateTestData.create_user(name='jack', password='test1')
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id)  # not, no key specified
        res = self.app.get(offset, status=403) # error


    def test_perform_reset_user_password_link_user_incorrect(self):
        # Make up a key - i.e. trying to hack this
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id='randomness',  # i.e. incorrect
                         key='randomness')
        res = self.app.get(offset, status=404)

    def test_perform_reset_activates_pending_user(self):
        password = 'password'
        params = { 'password1': password, 'password2': password }
        user = CreateTestData.create_user(name='pending_user',
                                          email='user@email.com')
        user.set_pending()
        create_reset_key(user)
        assert user.is_pending(), user.state

        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id,
                         key=user.reset_key)
        res = self.app.post(offset, params=params, status=302)

        user = model.User.get(user.id)
        assert user.is_active(), user

    def test_perform_reset_doesnt_activate_deleted_user(self):
        password = 'password'
        params = { 'password1': password, 'password2': password }
        user = CreateTestData.create_user(name='deleted_user',
                                          email='user@email.com')
        user.delete()
        create_reset_key(user)
        assert user.is_deleted(), user.state

        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id,
                         key=user.reset_key)
        res = self.app.post(offset, params=params, status=403)

        user = model.User.get(user.id)
        assert user.is_deleted(), user
