from zope.interface import implementer

from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IMetadataProvider

def default_password_compare(cleartext_password, stored_password_hash):
    try:
        from hashlib import sha1
    except ImportError: # Python < 2.5 #pragma NO COVERAGE
        from sha import new as sha1    #pragma NO COVERAGE

    # the stored password is stored as '{SHA}<SHA hexdigest>'.
    # or as a cleartext password (no {SHA} prefix)

    if stored_password_hash.startswith('{SHA}'):
        stored_password_hash = stored_password_hash[5:]
        if not isinstance(cleartext_password, type(b'')):
            cleartext_password = cleartext_password.encode('utf-8')
        digest = sha1(cleartext_password).hexdigest()
    else:
        digest = cleartext_password
        
    if stored_password_hash == digest:
        return True

    return False

def make_psycopg_conn_factory(**kw):
    # convenience (I always seem to use Postgres)
    def conn_factory(): #pragma NO COVERAGE
        import psycopg2 #pragma NO COVERAGE
        return psycopg2.connect(kw['repoze.who.dsn']) #pragma NO COVERAGE
    return conn_factory #pragma NO COVERAGE

@implementer(IAuthenticator)
class SQLAuthenticatorPlugin:

    def __init__(self, query, conn_factory, compare_fn):
        # statement should be pyformat dbapi binding-style, e.g.
        # "select user_id, password from users where login=%(login)s"
        self.query = query
        self.conn_factory = conn_factory
        self.compare_fn = compare_fn or default_password_compare
        self.conn = None

    # IAuthenticator
    def authenticate(self, environ, identity):
        if not 'login' in identity:
            return None
        if not self.conn:
            self.conn = self.conn_factory()
        curs = self.conn.cursor()
        curs.execute(self.query, identity)
        result = curs.fetchone()
        curs.close()
        if result:
            user_id, password = result
            if self.compare_fn(identity['password'], password):
                return user_id

@implementer(IMetadataProvider)
class SQLMetadataProviderPlugin:

    def __init__(self, name, query, conn_factory, filter):
        self.name = name
        self.query = query
        self.conn_factory = conn_factory
        self.filter = filter
        self.conn = None

    # IMetadataProvider
    def add_metadata(self, environ, identity):
        if self.conn is None:
            self.conn = self.conn_factory()
        curs = self.conn.cursor()
        # can't use dots in names in python string formatting :-(
        identity['__userid'] = identity['repoze.who.userid']
        curs.execute(self.query, identity)
        result = curs.fetchall()
        if self.filter:
            result = self.filter(result)
        curs.close()
        del identity['__userid']
        identity[self.name] =  result

def make_authenticator_plugin(query=None, conn_factory=None,
                              compare_fn=None, **kw):
    from repoze.who.utils import resolveDotted
    if query is None:
        raise ValueError('query must be specified')
    if conn_factory is None:
        raise ValueError('conn_factory must be specified')
    try:
        conn_factory = resolveDotted(conn_factory)(**kw)
    except Exception as why:
        raise ValueError('conn_factory could not be resolved: %s' % why)
    if compare_fn is not None:
        compare_fn = resolveDotted(compare_fn)
    return SQLAuthenticatorPlugin(query, conn_factory, compare_fn)

def make_metadata_plugin(name=None, query=None, conn_factory=None,
                         filter=None, **kw):
    from repoze.who.utils import resolveDotted
    if name is None:
        raise ValueError('name must be specified')
    if query is None:
        raise ValueError('query must be specified')
    if conn_factory is None:
        raise ValueError('conn_factory must be specified')
    try:
        conn_factory = resolveDotted(conn_factory)(**kw)
    except Exception as why:
        raise ValueError('conn_factory could not be resolved: %s' % why)
    if filter is not None:
        filter = resolveDotted(filter)
    return SQLMetadataProviderPlugin(name, query, conn_factory, filter)
    
