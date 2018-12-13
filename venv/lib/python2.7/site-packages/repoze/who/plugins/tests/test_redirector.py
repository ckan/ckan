import unittest


class TestRedirectorPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.redirector import RedirectorPlugin
        return RedirectorPlugin

    def _makeOne(self,
                 login_url='http://example.com/login.html',
                 came_from_param=None,
                 reason_param=None,
                 reason_header=None,
                ):
        return self._getTargetClass()(login_url,
                                      came_from_param=came_from_param,
                                      reason_param=reason_param,
                                      reason_header=reason_header)

    def _makeEnviron(self, path_info='/', identifier=None):
        from repoze.who._compat import StringIO
        if identifier is None:
            credentials = {'login':'chris', 'password':'password'}
            identifier = DummyIdentifier(credentials)
        content_type, body = encode_multipart_formdata()
        environ = {'wsgi.version': (1,0),
                   'wsgi.input': StringIO(body),
                   'wsgi.url_scheme':'http',
                   'SERVER_NAME': 'www.example.com',
                   'SERVER_PORT': '80',
                   'CONTENT_TYPE': content_type,
                   'CONTENT_LENGTH': len(body),
                   'REQUEST_METHOD': 'POST',
                   'repoze.who.plugins': {'cookie':identifier},
                   'QUERY_STRING': 'default=1',
                   'PATH_INFO': path_info,
                  }
        return environ

    def test_class_conforms_to_IChallenger(self):
        from zope.interface.verify import verifyClass
        from repoze.who.interfaces import IChallenger
        verifyClass(IChallenger, self._getTargetClass())

    def test_instance_conforms_to_IChallenger(self):
        from zope.interface.verify import verifyObject
        from repoze.who.interfaces import IChallenger
        verifyObject(IChallenger, self._makeOne())

    def test_ctor_w_reason_param_wo_reason_header(self):
        self.assertRaises(ValueError, self._makeOne,
                                        reason_param='reason',
                                        reason_header=None)

    def test_ctor_wo_reason_param_w_reason_header(self):
        self.assertRaises(ValueError, self._makeOne,
                                        reason_param=None,
                                        reason_header='X-Reason')

    def test_challenge(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from',
                               reason_param='reason',
                               reason_header='X-Authorization-Failure-Reason',
                              )
        environ = self._makeEnviron()
        app = plugin.challenge(environ, '401 Unauthorized', [('app', '1')],
                               [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[0][0], 'forget')
        self.assertEqual(sr.headers[0][1], '1')
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 1)
        came_from_key, came_from_value = parts_qsl[0]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')
        headers = sr.headers
        self.assertEqual(sr.headers[2][0], 'Content-Length')
        self.assertEqual(sr.headers[2][1], '165')
        self.assertEqual(sr.headers[3][0], 'Content-Type')
        self.assertEqual(sr.headers[3][1], 'text/plain; charset=UTF-8')
        self.assertEqual(sr.status, '302 Found')

    def test_challenge_with_reason_header(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from',
                               reason_param='reason',
                               reason_header='X-Authorization-Failure-Reason',
                              )
        environ = self._makeEnviron()
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [('X-Authorization-Failure-Reason', 'you are ugly')],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 2)
        parts_qsl.sort()
        came_from_key, came_from_value = parts_qsl[0]
        reason_key, reason_value = parts_qsl[1]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')
        self.assertEqual(reason_key, 'reason')
        self.assertEqual(reason_value, 'you are ugly')

    def test_challenge_with_custom_reason_header(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from',
                               reason_param='reason',
                               reason_header='X-Custom-Auth-Failure',
                              )
        environ = self._makeEnviron()
        environ['came_from'] = 'http://example.com/came_from'
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [('X-Authorization-Failure-Reason', 'you are ugly')],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 1)
        came_from_key, came_from_value = parts_qsl[0]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')

    def test_challenge_w_reason_no_reason_param_no_came_from_param(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne()
        environ = self._makeEnviron()
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [('X-Authorization-Failure-Reason', 'you are ugly')],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[0][0], "forget")
        self.assertEqual(sr.headers[0][1], "1")
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 0)
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')

    def test_challenge_w_reason_no_reason_param_w_came_from_param(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from',
                              )
        environ = self._makeEnviron()
        environ['came_from'] = 'http://example.com/came_from'
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [('X-Authorization-Failure-Reason', 'you are ugly')],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 1)
        came_from_key, came_from_value = parts_qsl[0]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')

    def test_challenge_with_reason_and_custom_reason_param(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from',
                               reason_param='auth_failure',
                               reason_header='X-Custom-Auth-Failure',
                              )
        environ = self._makeEnviron()
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [('X-Authorization-Failure-Reason', 'wrong reason'),
             ('X-Custom-Auth-Failure', 'you are ugly')],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 2)
        parts_qsl.sort()
        reason_key, reason_value = parts_qsl[0]
        came_from_key, came_from_value = parts_qsl[1]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')
        self.assertEqual(reason_key, 'auth_failure')
        self.assertEqual(reason_value, 'you are ugly')

    def test_challenge_wo_reason_w_came_from_param(self):
        from ..._compat import parse_qsl
        from ..._compat import urlparse
        plugin = self._makeOne(came_from_param='came_from')
        environ = self._makeEnviron()
        app = plugin.challenge(
            environ, '401 Unauthorized',
            [],
            [('forget', '1')])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[1][0], 'Location')
        url = sr.headers[1][1]
        parts = urlparse(url)
        parts_qsl = parse_qsl(parts[4])
        self.assertEqual(len(parts_qsl), 1)
        came_from_key, came_from_value = parts_qsl[0]
        self.assertEqual(parts[0], 'http')
        self.assertEqual(parts[1], 'example.com')
        self.assertEqual(parts[2], '/login.html')
        self.assertEqual(parts[3], '')
        self.assertEqual(came_from_key, 'came_from')
        self.assertEqual(came_from_value, 'http://www.example.com/?default=1')

    def test_challenge_with_setcookie_from_app(self):
        plugin = self._makeOne(came_from_param='came_from',
                               reason_param='reason',
                               reason_header='X-Authorization-Failure-Reason',
                              )
        environ = self._makeEnviron()
        app = plugin.challenge(
            environ,
            '401 Unauthorized',
            [('app', '1'), ('set-cookie','a'), ('set-cookie','b')],
            [])
        sr = DummyStartResponse()
        result = b''.join(app(environ, sr)).decode('ascii')
        self.assertTrue(result.startswith('302 Found'))
        self.assertEqual(sr.headers[0][0], 'set-cookie')
        self.assertEqual(sr.headers[0][1], 'a')
        self.assertEqual(sr.headers[1][0], 'set-cookie')
        self.assertEqual(sr.headers[1][1], 'b')

class Test_make_redirecting_plugin(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from repoze.who.plugins.redirector import make_plugin
        return make_plugin(*args, **kw)

    def test_no_login_url_raises(self):
        self.assertRaises(ValueError, self._callFUT, None)

    def test_defaults(self):
        plugin = self._callFUT('/go_there')
        self.assertEqual(plugin.login_url, '/go_there')
        self.assertEqual(plugin.came_from_param, None)
        self.assertEqual(plugin.reason_param, None)
        self.assertEqual(plugin.reason_header, None)

    def test_explicit_came_from_param(self):
        plugin = self._callFUT('/go_there', came_from_param='whence')
        self.assertEqual(plugin.login_url, '/go_there')
        self.assertEqual(plugin.came_from_param, 'whence')
        self.assertEqual(plugin.reason_param, None)
        self.assertEqual(plugin.reason_header, None)

    def test_explicit_reason_param(self):
        plugin = self._callFUT('/go_there', reason_param='why')
        self.assertEqual(plugin.login_url, '/go_there')
        self.assertEqual(plugin.came_from_param, None)
        self.assertEqual(plugin.reason_param, 'why')
        self.assertEqual(plugin.reason_header, 'X-Authorization-Failure-Reason')

    def test_explicit_reason_header_param_no_reason_param_raises(self):
        self.assertRaises(Exception, self._callFUT, '/go_there',
                                                    reason_header='X-Reason')

    def test_explicit_reason_header_param(self):
        plugin = self._callFUT('/go_there', reason_param='why',
                                            reason_header='X-Reason')
        self.assertEqual(plugin.login_url, '/go_there')
        self.assertEqual(plugin.came_from_param, None)
        self.assertEqual(plugin.reason_param, 'why')
        self.assertEqual(plugin.reason_header, 'X-Reason')

class DummyIdentifier(object):
    forgotten = False
    remembered = False

    def __init__(self, credentials=None, remember_headers=None,
                 forget_headers=None, replace_app=None):
        self.credentials = credentials
        self.remember_headers = remember_headers
        self.forget_headers = forget_headers
        self.replace_app = replace_app

class DummyStartResponse:
    def __call__(self, status, headers, exc_info=None):
        self.status = status
        self.headers = headers
        self.exc_info = exc_info
        return []

def encode_multipart_formdata():
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body
