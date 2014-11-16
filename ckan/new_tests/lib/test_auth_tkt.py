from ckan.new_tests import helpers
from ckan.lib.auth_tkt import (CkanAuthTktCookiePlugin,
                               _set_substring,
                               make_plugin)


class TestSetSubstring(object):

    '''Tests for auth_tkt._set_substring method.'''

    def test_set_substring__value_has_substring_and_substring_should_be_present(self):
        '''Substring should be retained in value'''
        value = "I love my kitten, it is sweet."
        substring = "kitten"
        presence = True
        new_value = _set_substring(value, substring, presence)
        assert new_value == value

    def test_set_substring__value_has_substring_and_substring_should_not_be_present(self):
        '''Substring should be removed from value.'''
        value = "I love my kitten, it is sweet."
        substring = "kitten"
        presence = False
        new_value = _set_substring(value, substring, presence)
        assert new_value == "I love my , it is sweet."

    def test_set_substring__value_doesnot_have_substring_and_substring_should_be_present(self):
        '''Substring is appended to value.'''
        value = "I wish I had a "
        substring = "kitten"
        presence = True
        new_value = _set_substring(value, substring, presence)
        assert new_value == 'I wish I had a kitten'

    def test_set_substring__value_doesnot_have_substring_and_substring_should_not_be_present(self):
        '''Substring isn't appended to value.'''
        value = "I don't have one."
        substring = "kitten"
        presence = False
        new_value = _set_substring(value, substring, presence)
        assert new_value == "I don't have one."


class TestEnsureHttpOnlyForCookies(object):

    '''Tests for CkanAuthTktCookiePlugin._ensure_httponly_for_cookies method'''

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

    def test_ensure_httponly_for_cookies__should_have_httponly(self):
        '''Cookie values should contain HttpOnly.'''
        plugin = self._make_plugin(httponly=True)
        cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost')
        ]
        ensured_cookies = plugin._ensure_httponly_for_cookies(cookies)
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost; HttpOnly')
        ]
        assert ensured_cookies == expected_cookies

    def test_ensure_httponly_for_cookies__should_have_httponly_already_do(self):
        '''
        Cookie values should contain HttpOnly, they already to so nothing
        should change.
        '''
        plugin = self._make_plugin(httponly=True)
        cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost; HttpOnly')
        ]
        ensured_cookies = plugin._ensure_httponly_for_cookies(cookies)
        assert ensured_cookies == cookies

    def test_ensure_httponly_for_cookies__should_not_have_httponly_already_absent(self):
        '''
        Cookie values should not contain HttpOnly. They don't so nothing
        should change.
        '''
        plugin = self._make_plugin(httponly=False)
        cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost')
        ]
        ensured_cookies = plugin._ensure_httponly_for_cookies(cookies)
        assert ensured_cookies == cookies

    def test_ensure_httponly_for_cookies__should_not_have_httponly(self):
        '''
        Cookie values should not contain HttpOnly, they do so it should be
        removed.
        '''
        plugin = self._make_plugin(httponly=False)
        cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost; HttpOnly'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost; HttpOnly')
        ]
        ensured_cookies = plugin._ensure_httponly_for_cookies(cookies)
        expected_cookies = [
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=localhost'),
            ('Set-Cookie', 'auth_tkt="HELLO"; Path=/; Domain=.localhost')
        ]
        assert ensured_cookies == expected_cookies


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
        The returned cookies are in the format we expect, with secure flag.
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
