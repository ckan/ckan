import unittest


class TestSQLAuthenticatorPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.sql import SQLAuthenticatorPlugin
        return SQLAuthenticatorPlugin

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
        verifyClass(IAuthenticator, klass, tentative=True)

    def test_authenticate_noresults(self):
        dummy_factory = DummyConnectionFactory([])
        plugin = self._makeOne('select foo from bar', dummy_factory,
                               compare_succeed)
        environ = self._makeEnviron()
        identity = {'login':'foo', 'password':'bar'}
        result = plugin.authenticate(environ, identity)
        self.assertEqual(result, None)
        self.assertEqual(dummy_factory.query, 'select foo from bar')
        self.assertEqual(dummy_factory.closed, True)

    def test_authenticate_comparefail(self):
        dummy_factory = DummyConnectionFactory([ ['userid', 'password'] ])
        plugin = self._makeOne('select foo from bar', dummy_factory,
                               compare_fail)
        environ = self._makeEnviron()
        identity = {'login':'fred', 'password':'bar'}
        result = plugin.authenticate(environ, identity)
        self.assertEqual(result, None)
        self.assertEqual(dummy_factory.query, 'select foo from bar')
        self.assertEqual(dummy_factory.closed, True)

    def test_authenticate_comparesuccess(self):
        dummy_factory = DummyConnectionFactory([ ['userid', 'password'] ])
        plugin = self._makeOne('select foo from bar', dummy_factory,
                               compare_succeed)
        environ = self._makeEnviron()
        identity = {'login':'fred', 'password':'bar'}
        result = plugin.authenticate(environ, identity)
        self.assertEqual(result, 'userid')
        self.assertEqual(dummy_factory.query, 'select foo from bar')
        self.assertEqual(dummy_factory.closed, True)

    def test_authenticate_nologin(self):
        dummy_factory = DummyConnectionFactory([ ['userid', 'password'] ])
        plugin = self._makeOne('select foo from bar', dummy_factory,
                               compare_succeed)
        environ = self._makeEnviron()
        identity = {}
        result = plugin.authenticate(environ, identity)
        self.assertEqual(result, None)
        self.assertEqual(dummy_factory.query, None)
        self.assertEqual(dummy_factory.closed, False)

class TestDefaultPasswordCompare(unittest.TestCase):

    def _getFUT(self):
        from repoze.who.plugins.sql import default_password_compare
        return default_password_compare

    def _get_sha_hex_digest(self, clear='password'):
        try:
            from hashlib import sha1
        except ImportError:  # pragma: no cover Py3k
            from sha import new as sha1
        if not isinstance(clear, type(b'')):  # pragma: no cover Py3k
            clear = clear.encode('utf-8')
        return sha1(clear).hexdigest()

    def test_shaprefix_success(self):
        stored = '{SHA}' +  self._get_sha_hex_digest()
        compare = self._getFUT()
        result = compare('password', stored)
        self.assertEqual(result, True)

    def test_shaprefix_w_unicode_cleartext(self):
        from repoze.who._compat import u
        stored = '{SHA}' +  self._get_sha_hex_digest()
        compare = self._getFUT()
        result = compare(u('password'), stored)
        self.assertEqual(result, True)

    def test_shaprefix_fail(self):
        stored = '{SHA}' + self._get_sha_hex_digest()
        compare = self._getFUT()
        result = compare('notpassword', stored)
        self.assertEqual(result, False)

    def test_noprefix_success(self):
        stored = 'password'
        compare = self._getFUT()
        result = compare('password', stored)
        self.assertEqual(result, True)

    def test_noprefix_fail(self):
        stored = 'password'
        compare = self._getFUT()
        result = compare('notpassword', stored)
        self.assertEqual(result, False)

class TestSQLMetadataProviderPlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.sql import SQLMetadataProviderPlugin
        return SQLMetadataProviderPlugin

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_implements(self):
        from zope.interface.verify import verifyClass
        from repoze.who.interfaces import IMetadataProvider
        klass = self._getTargetClass()
        verifyClass(IMetadataProvider, klass, tentative=True)

    def test_add_metadata(self):
        dummy_factory = DummyConnectionFactory([ [1, 2, 3] ])
        def dummy_filter(results):
            return results
        plugin = self._makeOne('md', 'select foo from bar', dummy_factory,
                               dummy_filter)
        environ = {}
        identity = {'repoze.who.userid':1}
        plugin.add_metadata(environ, identity)
        self.assertEqual(dummy_factory.closed, True)
        self.assertEqual(identity['md'], [ [1,2,3] ])
        self.assertEqual(dummy_factory.query, 'select foo from bar')
        self.assertFalse('__userid' in identity)

class TestMakeSQLAuthenticatorPlugin(unittest.TestCase):

    def _getFUT(self):
        from repoze.who.plugins.sql import make_authenticator_plugin
        return make_authenticator_plugin

    def test_noquery(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, None, 'conn', 'compare')

    def test_no_connfactory(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, 'statement', None, 'compare')

    def test_bad_connfactory(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, 'statement', 'does.not:exist', None)

    def test_connfactory_specd(self):
        f = self._getFUT()
        plugin = f('statement',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory',
                   None)
        self.assertEqual(plugin.query, 'statement')
        self.assertEqual(plugin.conn_factory, DummyConnFactory)
        from repoze.who.plugins.sql import default_password_compare
        self.assertEqual(plugin.compare_fn, default_password_compare)

    def test_comparefunc_specd(self):
        f = self._getFUT()
        plugin = f('statement',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory')
        self.assertEqual(plugin.query, 'statement')
        self.assertEqual(plugin.conn_factory, DummyConnFactory)
        self.assertEqual(plugin.compare_fn, make_dummy_connfactory)

class TestMakeSQLMetadataProviderPlugin(unittest.TestCase):

    def _getFUT(self):
        from repoze.who.plugins.sql import make_metadata_plugin
        return make_metadata_plugin

    def test_no_name(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f)

    def test_no_query(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, 'name', None, None)

    def test_no_connfactory(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, 'name', 'statement', None)

    def test_bad_connfactory(self):
        f = self._getFUT()
        self.assertRaises(ValueError, f, 'name', 'statement',
                          'does.not:exist', None)

    def test_connfactory_specd(self):
        f = self._getFUT()
        plugin = f('name', 'statement',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory',
                   None)
        self.assertEqual(plugin.name, 'name')
        self.assertEqual(plugin.query, 'statement')
        self.assertEqual(plugin.conn_factory, DummyConnFactory)
        self.assertEqual(plugin.filter, None)

    def test_comparefn_specd(self):
        f = self._getFUT()
        plugin = f('name', 'statement',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory',
                   'repoze.who.plugins.tests.test_sql:make_dummy_connfactory')
        self.assertEqual(plugin.name, 'name')
        self.assertEqual(plugin.query, 'statement')
        self.assertEqual(plugin.conn_factory, DummyConnFactory)
        self.assertEqual(plugin.filter, make_dummy_connfactory)


class DummyConnectionFactory:
    # acts as all of: a factory, a connection, and a cursor
    closed = False
    query = None
    def __init__(self, results):
        self.results = results

    def __call__(self):
        return self

    def cursor(self):
        return self

    def execute(self, query, *arg):
        self.query = query
        self.bindargs = arg

    def fetchall(self):
        return self.results

    def fetchone(self):
        if self.results:
            return self.results[0]
        return []

    def close(self):
        self.closed = True

def compare_fail(cleartext, stored):
    return False

def compare_succeed(cleartext, stored):
    return True

class _DummyConnFactory:
    pass

DummyConnFactory = _DummyConnFactory()

def make_dummy_connfactory(**kw):
    return DummyConnFactory
