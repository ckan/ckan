# encoding: utf-8

from nose import tools as nose_tools

from ckan.tests import helpers
from ckan.lib.auth_tkt import make_plugin


class TestCkanAuthTktCookiePlugin(helpers.FunctionalTestBase):

    '''
    Test the added methods used by this subclass of
    repoze.who.plugins.auth_tkt.AuthTktCookiePlugin

    Subclassing FunctionalTestBase ensures the original config is restored
    after each test.
    '''

    @helpers.change_config('who.httponly', True)
    def test_httponly_expected_cookies_with_config_httponly_true(self):
        '''
        The returned cookies are in the format we expect, with HttpOnly flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly')
        ]
        assert cookies == expected_cookies

    @helpers.change_config('who.httponly', False)
    def test_httponly_expected_cookies_with_config_httponly_false(self):
        '''
        The returned cookies are in the format we expect, without HttpOnly
        flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0')
        ]
        assert cookies == expected_cookies

    def test_httponly_expected_cookies_without_config_httponly(self):
        '''
        The returned cookies are in the format we expect, with HttpOnly flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly')
        ]
        assert cookies == expected_cookies

    @helpers.change_config('who.secure', True)
    def test_secure_expected_cookies_with_config_secure_true(self):
        '''
        The returned cookies are in the format we expect, with secure flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; secure; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; secure; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; secure; HttpOnly')
        ]
        assert cookies == expected_cookies

    @helpers.change_config('who.secure', False)
    def test_secure_expected_cookies_with_config_secure_false(self):
        '''
        The returned cookies are in the format we expect, without secure
        flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly')
        ]
        assert cookies == expected_cookies

    def test_secure_expected_cookies_without_config_secure(self):
        '''
        The returned cookies are in the format we expect, without secure flag.
        '''
        plugin = make_plugin(secret='sosecret')
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='HELLO')
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly')
        ]
        assert cookies == expected_cookies

    def test_timeout_not_set_in_config(self):
        '''
        Creating a CkanAuthTktCookiePlugin instance without setting timeout in
        config sets correct values in CkanAuthTktCookiePlugin instance.
        '''
        plugin = make_plugin(secret='sosecret')

        nose_tools.assert_equal(plugin.timeout, None)
        nose_tools.assert_equal(plugin.reissue_time, None)

    @helpers.change_config('who.timeout', 9000)
    def test_timeout_set_in_config(self):
        '''
        Setting who.timeout in config sets correct values in
        CkanAuthTktCookiePlugin instance.
        '''
        plugin = make_plugin(secret='sosecret')

        nose_tools.assert_equal(plugin.timeout, 9000)
        nose_tools.assert_equal(plugin.reissue_time, 900)

    @helpers.change_config('who.timeout', 9000)
    @helpers.change_config('who.reissue_time', 200)
    def test_reissue_set_in_config(self):
        '''
        Setting who.reissue in config sets correct values in
        CkanAuthTktCookiePlugin instance.
        '''
        plugin = make_plugin(secret='sosecret')

        nose_tools.assert_equal(plugin.timeout, 9000)
        nose_tools.assert_equal(plugin.reissue_time, 200)
