import ckan

import ckan.lib.create_test_data as ctd
import ckan.lib.authenticator as authenticator

CreateTestData = ctd.CreateTestData


class TestUsernamePasswordAuthenticator(object):
    @classmethod
    def setup_class(cls):
        auth = authenticator.UsernamePasswordAuthenticator()
        cls.authenticate = auth.authenticate

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_authenticate_succeeds_if_login_and_password_are_correct(self):
        environ = {}
        password = 'somepass'
        user = CreateTestData.create_user('a_user', **{'password': password})
        identity = {'login': user.name, 'password': password}

        username = self.authenticate(environ, identity)
        assert username == user.name, username

    def test_authenticate_fails_if_user_is_deleted(self):
        environ = {}
        password = 'somepass'
        user = CreateTestData.create_user('a_user', **{'password': password})
        identity = {'login': user.name, 'password': password}
        user.delete()

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        environ = {}
        password = 'somepass'
        user = CreateTestData.create_user('a_user', **{'password': password})
        identity = {'login': user.name, 'password': password}
        user.set_pending()

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_password_is_wrong(self):
        environ = {}
        user = CreateTestData.create_user('a_user')
        identity = {'login': user.name, 'password': 'wrong-password'}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_no_login_or_pass(self):
        environ = {}
        identity = {}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_login(self):
        environ = {}
        identity = {'login': 'some-user'}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_received_just_password(self):
        environ = {}
        identity = {'password': 'some-password'}
        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_doesnt_exist(self):
        environ = {}
        identity = {'login': 'inexistent-user'}
        assert self.authenticate(environ, identity) is None


class TestOpenIDAuthenticator(object):
    @classmethod
    def setup_class(cls):
        auth = authenticator.OpenIDAuthenticator()
        cls.authenticate = auth.authenticate

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_authenticate_succeeds_if_openid_is_correct(self):
        environ = {}
        openid = 'some-openid-key'
        user = CreateTestData.create_user('a_user', **{'openid': openid})
        identity = {'login': user.name,
                    'repoze.who.plugins.openid.userid': openid}

        username = self.authenticate(environ, identity)
        assert username == user.name, username

    def test_authenticate_fails_if_openid_is_incorrect(self):
        environ = {}
        openid = 'wrong-openid-key'
        user = CreateTestData.create_user('a_user')
        identity = {'login': user.name,
                    'repoze.who.plugins.openid.userid': openid}

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_is_deleted(self):
        environ = {}
        openid = 'some-openid-key'
        user = CreateTestData.create_user('a_user', **{'openid': openid})
        user.delete()
        identity = {'login': user.name,
                    'repoze.who.plugins.openid.userid': openid}

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_is_pending(self):
        environ = {}
        openid = 'some-openid-key'
        user = CreateTestData.create_user('a_user', **{'openid': openid})
        user.set_pending()
        identity = {'login': user.name,
                    'repoze.who.plugins.openid.userid': openid}

        assert self.authenticate(environ, identity) is None

    def test_authenticate_fails_if_user_have_no_openid(self):
        environ = {}
        identity = {}
        assert self.authenticate(environ, identity) is None
