import unittest


class TestHTPasswdPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.htpasswd import HTPasswdPlugin
        return HTPasswdPlugin

    def _makeOne(self, *arg, **kw):
        plugin = self._getTargetClass()(*arg, **kw)
        return plugin

    def _makeEnviron(self):
        environ = {}
        environ['wsgi.version'] = (1,0)
        return environ

    def test_implements(self):
        from zope.interface.verify import verifyClass
        from repoze.who.interfaces import IAuthenticator
        klass = self._getTargetClass()
        verifyClass(IAuthenticator, klass)

    def test_authenticate_nocreds(self):
        from repoze.who._compat import StringIO
        io = StringIO()
        plugin = self._makeOne(io, None)
        environ = self._makeEnviron()
        creds = {}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, None)

    def test_authenticate_nolines(self):
        from repoze.who._compat import StringIO
        io = StringIO()
        def check(password, hashed):
            return True
        plugin = self._makeOne(io, check)
        environ = self._makeEnviron()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, None)

    def test_authenticate_nousermatch(self):
        from repoze.who._compat import StringIO
        io = StringIO('nobody:foo')
        def check(password, hashed):
            return True
        plugin = self._makeOne(io, check)
        environ = self._makeEnviron()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, None)

    def test_authenticate_match(self):
        from repoze.who._compat import StringIO
        io = StringIO('chrism:pass')
        def check(password, hashed):
            return True
        plugin = self._makeOne(io, check)
        environ = self._makeEnviron()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, 'chrism')

    def test_authenticate_badline(self):
        from repoze.who._compat import StringIO
        io = StringIO('badline\nchrism:pass')
        def check(password, hashed):
            return True
        plugin = self._makeOne(io, check)
        environ = self._makeEnviron()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, 'chrism')

    def test_authenticate_filename(self):
        import os
        here = os.path.abspath(os.path.dirname(__file__))
        htpasswd = os.path.join(here, 'fixtures', 'test.htpasswd')
        def check(password, hashed):
            return True
        plugin = self._makeOne(htpasswd, check)
        environ = self._makeEnviron()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, 'chrism')

    def test_authenticate_bad_filename_logs_to_repoze_who_logger(self):
        import os
        here = os.path.abspath(os.path.dirname(__file__))
        htpasswd = os.path.join(here, 'fixtures', 'test.htpasswd.nonesuch')
        def check(password, hashed): # pragma: no cover
            return True
        plugin = self._makeOne(htpasswd, check)
        environ = self._makeEnviron()
        class DummyLogger:
            warnings = []
            def warn(self, msg):
                self.warnings.append(msg)
        logger = environ['repoze.who.logger'] = DummyLogger()
        creds = {'login':'chrism', 'password':'pass'}
        result = plugin.authenticate(environ, creds)
        self.assertEqual(result, None)
        self.assertEqual(len(logger.warnings), 1)
        self.assertTrue('could not open htpasswd' in logger.warnings[0])

    def test_crypt_check(self):
        import sys
        # win32 does not have a crypt library, don't
        # fail here
        if "win32" == sys.platform: # pragma: no cover
            return

        from crypt import crypt
        salt = '123'
        hashed = crypt('password', salt)
        from repoze.who.plugins.htpasswd import crypt_check
        self.assertEqual(crypt_check('password', hashed), True)
        self.assertEqual(crypt_check('notpassword', hashed), False)

    def test_sha1_check(self):
        from base64 import standard_b64encode
        from hashlib import sha1
        from repoze.who._compat import must_encode
        from repoze.who.plugins.htpasswd import sha1_check

        encrypted_string = standard_b64encode(sha1(
                                must_encode("password")).digest())
        self.assertEqual(sha1_check('password',
                         "%s%s" % ("{SHA}", encrypted_string)), True)
        self.assertEqual(sha1_check('notpassword',
                         "%s%s" % ("{SHA}", encrypted_string)), False)

    def test_plain_check(self):
        from repoze.who.plugins.htpasswd import plain_check
        self.assertTrue(plain_check('password', 'password'))
        self.assertFalse(plain_check('notpassword', 'password'))

    def test_factory_no_filename_raises(self):
        from repoze.who.plugins.htpasswd import make_plugin
        self.assertRaises(ValueError, make_plugin)

    def test_factory_no_check_fn_raises(self):
        from repoze.who.plugins.htpasswd import make_plugin
        self.assertRaises(ValueError, make_plugin, 'foo')

    def test_factory(self):
        from repoze.who.plugins.htpasswd import make_plugin
        from repoze.who.plugins.htpasswd import crypt_check
        plugin = make_plugin('foo',
                             'repoze.who.plugins.htpasswd:crypt_check')
        self.assertEqual(plugin.filename, 'foo')
        self.assertEqual(plugin.check, crypt_check)
