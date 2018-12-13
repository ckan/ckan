import unittest


class CompatTests(unittest.TestCase):

    def test_REQUEST_METHOD_miss(self):
        # PEP 3333 says CONTENT_TYPE is mandatory
        from .._compat import REQUEST_METHOD
        self.assertRaises(KeyError, REQUEST_METHOD, {})

    def test_REQUEST_METHOD_hit(self):
        from .._compat import REQUEST_METHOD
        self.assertEqual(REQUEST_METHOD({'REQUEST_METHOD': 'FOO'}), 'FOO')

    def test_CONTENT_TYPE_miss(self):
        # PEP 3333 says CONTENT_TYPE is optional
        from .._compat import CONTENT_TYPE
        self.assertEqual(CONTENT_TYPE({}), '')

    def test_CONTENT_TYPE_hit(self):
        from .._compat import CONTENT_TYPE
        self.assertEqual(CONTENT_TYPE({'CONTENT_TYPE': 'text/html'}),
                         'text/html')

    def test_USER_AGENT_miss(self):
        from .._compat import USER_AGENT
        self.assertEqual(USER_AGENT({}), None)

    def test_USER_AGENT_hit(self):
        from .._compat import USER_AGENT
        self.assertEqual(USER_AGENT({'HTTP_USER_AGENT': 'FOO'}), 'FOO')

    def test_AUTHORIZATION_miss(self):
        from .._compat import AUTHORIZATION
        self.assertEqual(AUTHORIZATION({}), '')

    def test_AUTHORIZATION_hit(self):
        from .._compat import AUTHORIZATION
        self.assertEqual(AUTHORIZATION({'HTTP_AUTHORIZATION': 'FOO'}), 'FOO')

    def test_get_cookies_no_cache_ok_header_value(self):
        from .._compat import get_cookies
        from .._compat import SimpleCookie
        environ = {'HTTP_COOKIE': 'qux=spam'}
        cookies = get_cookies(environ)
        self.assertTrue(isinstance(cookies, SimpleCookie))
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies['qux'].value, 'spam')
        self.assertEqual(environ['paste.cookies'], (cookies, 'qux=spam'))

    def test_get_cookies_w_cache_miss(self):
        from .._compat import get_cookies
        from .._compat import SimpleCookie
        environ = {'HTTP_COOKIE': 'qux=spam',
                   'paste.cookies': (object(), 'foo=bar'),
                  }
        cookies = get_cookies(environ)
        self.assertTrue(isinstance(cookies, SimpleCookie))
        self.assertEqual(len(cookies), 1)
        self.assertEqual(cookies['qux'].value, 'spam')
        self.assertEqual(environ['paste.cookies'], (cookies, 'qux=spam'))

    def test_get_cookies_w_cache_hit(self):
        from .._compat import get_cookies
        from .._compat import SimpleCookie
        existing = SimpleCookie()
        existing['foo'] = 'bar'
        environ = {'HTTP_COOKIE': 'qux=spam',
                   'paste.cookies': (existing, 'qux=spam'),
                  }
        cookies = get_cookies(environ)
        self.assertTrue(cookies is existing)

    def test_construct_url(self):
        from .._compat import construct_url
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        self.assertEqual(construct_url(environ), 'http://example.com/')

    def test_header_value_miss(self):
        from .._compat import header_value
        self.assertEqual(header_value([], 'nonesuch'), '')

    def test_header_value_simple(self):
        from .._compat import header_value
        self.assertEqual(header_value([('simple', 'SIMPLE')], 'simple'),
                         'SIMPLE')

    def test_must_decode_non_string(self):
        from .._compat import must_decode
        foo = object()
        self.assertTrue(must_decode(foo) is foo)

    def test_must_decode_unicode(self):
        from .._compat import must_decode
        from .._compat import u
        foo = u('foo')
        self.assertTrue(must_decode(foo) is foo)

    def test_must_decode_utf8(self):
        from .._compat import must_decode
        foo = b'b\xc3\xa2tard'
        self.assertEqual(must_decode(foo), foo.decode('utf-8'))

    def test_must_decode_latin1(self):
        from .._compat import must_decode
        foo = b'b\xe2tard'
        self.assertEqual(must_decode(foo), foo.decode('latin1'))

    def test_must_encode_non_string(self):
        from .._compat import must_encode
        foo = object()
        self.assertTrue(must_encode(foo) is foo)

    def test_must_encode_unicode(self):
        from .._compat import must_encode
        from .._compat import u
        foo = u('foo')
        self.assertEqual(must_encode(foo), foo.encode('utf-8'))

    def test_must_encode_utf8(self):
        from .._compat import must_encode
        foo = b'b\xc3\xa2tard'
        self.assertTrue(must_encode(foo) is foo)

    def test_must_encode_latin1(self):
        from .._compat import must_encode
        foo = b'b\xe2tard'
        self.assertTrue(must_encode(foo) is foo)

