from ckan.lib.auth_tkt import CkanAuthTktCookiePlugin
from ckan.lib.auth_tkt import _set_substring


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

    def test_httponly_present(self):
        '''HttpOnly flag should be present in cookie values.'''
        plugin = self._make_plugin(httponly=True)
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='ANYTHING')
        for cookie in cookies:
            assert 'HttpOnly' in cookie[1]

    def test_httponly_absent(self):
        '''HttpOnly flag should be absent in cookie values.'''
        plugin = self._make_plugin(httponly=False)
        cookies = plugin._get_cookies(environ={'SERVER_NAME': '0.0.0.0'},
                                      value='ANYTHING')
        for cookie in cookies:
            assert 'HttpOnly' not in cookie[1]
