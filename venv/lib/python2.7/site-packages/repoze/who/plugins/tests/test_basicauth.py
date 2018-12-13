import unittest


class TestBasicAuthPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.basicauth import BasicAuthPlugin
        return BasicAuthPlugin

    def _makeOne(self, *arg, **kw):
        plugin = self._getTargetClass()(*arg, **kw)
        return plugin

    def _makeEnviron(self, kw=None):
        from wsgiref.util import setup_testing_defaults
        environ = {}
        setup_testing_defaults(environ)
        if kw is not None:
            environ.update(kw)
        return environ

    def test_implements(self):
        from zope.interface.verify import verifyClass
        from repoze.who.interfaces import IChallenger
        from repoze.who.interfaces import IIdentifier
        klass = self._getTargetClass()
        verifyClass(IChallenger, klass)
        verifyClass(IIdentifier, klass)

    def test_challenge(self):
        plugin = self._makeOne('realm')
        environ = self._makeEnviron()
        result = plugin.challenge(environ, '401 Unauthorized', [], [])
        self.assertNotEqual(result, None)
        app_iter = result(environ, lambda *arg: None)
        items = []
        for item in app_iter:
            items.append(item)
        response = b''.join(items).decode('utf-8')
        self.assertTrue(response.startswith('401 Unauthorized'))

    def test_identify_noauthinfo(self):
        plugin = self._makeOne('realm')
        environ = self._makeEnviron()
        creds = plugin.identify(environ)
        self.assertEqual(creds, None)

    def test_identify_nonbasic(self):
        plugin = self._makeOne('realm')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Digest abc'})
        creds = plugin.identify(environ)
        self.assertEqual(creds, None)

    def test_identify_basic_badencoding(self):
        plugin = self._makeOne('realm')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Basic abc'})
        creds = plugin.identify(environ)
        self.assertEqual(creds, None)

    def test_identify_basic_badrepr(self):
        from repoze.who._compat import encodebytes
        plugin = self._makeOne('realm')
        value = encodebytes(b'foo').decode('ascii')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Basic %s' % value})
        creds = plugin.identify(environ)
        self.assertEqual(creds, None)

    def test_identify_basic_ok(self):
        from repoze.who._compat import encodebytes
        plugin = self._makeOne('realm')
        value = encodebytes(b'foo:bar').decode('ascii')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Basic %s' % value})
        creds = plugin.identify(environ)
        self.assertEqual(creds, {'login':'foo', 'password':'bar'})

    def test_identify_basic_ok_utf8_values(self):
        from repoze.who._compat import encodebytes
        LOGIN = b'b\xc3\xa2tard'
        PASSWD = b'l\xc3\xa0 demain'
        plugin = self._makeOne('realm')
        value = encodebytes(b':'.join((LOGIN, PASSWD))).decode('ascii')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Basic %s' % value})
        creds = plugin.identify(environ)
        self.assertEqual(creds, {'login': LOGIN.decode('utf-8'),
                                 'password': PASSWD.decode('utf-8')})

    def test_identify_basic_ok_latin1_values(self):
        from repoze.who._compat import encodebytes
        LOGIN = b'b\xe2tard'
        PASSWD = b'l\xe0 demain'
        plugin = self._makeOne('realm')
        value = encodebytes(b':'.join((LOGIN, PASSWD))).decode('ascii')
        environ = self._makeEnviron({'HTTP_AUTHORIZATION':'Basic %s' % value})
        creds = plugin.identify(environ)
        self.assertEqual(creds, {'login': LOGIN.decode('latin1'),
                                 'password': PASSWD.decode('latin1')})

    def test_remember(self):
        plugin = self._makeOne('realm')
        creds = {}
        environ = self._makeEnviron()
        result = plugin.remember(environ, creds)
        self.assertEqual(result, None)

    def test_forget(self):
        plugin = self._makeOne('realm')
        creds = {'login':'foo', 'password':'password'}
        environ = self._makeEnviron()
        result = plugin.forget(environ, creds)
        self.assertEqual(result, [('WWW-Authenticate', 'Basic realm="realm"')] )

    def test_challenge_forgetheaders_includes(self):
        plugin = self._makeOne('realm')
        creds = {'login':'foo', 'password':'password'}
        environ = self._makeEnviron()
        forget = plugin._get_wwwauth()
        result = plugin.challenge(environ, '401 Unauthorized', [], forget)
        self.assertTrue(forget[0] in result.headers.items())

    def test_challenge_forgetheaders_omits(self):
        plugin = self._makeOne('realm')
        creds = {'login':'foo', 'password':'password'}
        environ = self._makeEnviron()
        forget = plugin._get_wwwauth()
        result = plugin.challenge(environ, '401 Unauthorized', [], [])
        self.assertTrue(forget[0] in result.headers.items())

    def test_factory(self):
        from repoze.who.plugins.basicauth import make_plugin
        plugin = make_plugin('realm')
        self.assertEqual(plugin.realm, 'realm')

