from ckan.new_tests import helpers
from ckan.lib.auth_tkt import CkanAuthTktCookiePlugin, make_plugin


class TestCkanAuthTktCookiePlugin(object):

    '''
    Test the added methods used by this subclass of
    repoze.who.plugins.auth_tkt.AuthTktCookiePlugin
    '''

    def _make_plugin(self, httponly):
        '''Only httponly needs to be set.'''
        return CkanAuthTktCookiePlugin(httponly=httponly,
                                       secret=None,
                                       cookie_name='auth_tkt',
                                       secure=False,
                                       include_ip=False,
                                       timeout=None,
                                       reissue_time=None,
                                       userid_checker=None)

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
