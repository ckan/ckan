from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

from ckan.model import User, Session

class OpenIDAuthenticator(object):
    implements(IAuthenticator)
    
    def authenticate(self, environ, identity):
        if 'repoze.who.plugins.openid.userid' in identity:
            openid = identity.get('repoze.who.plugins.openid.userid')
            user = User.by_openid(openid)
            if user is None:
                return None
            else:
                return user.name
        return None
    

class UsernamePasswordAuthenticator(object):
    implements(IAuthenticator)
    
    def authenticate(self, environ, identity):
        if not 'login' in identity or not 'password' in identity:
            return None
        user = User.by_name(identity.get('login'))
        if user is None: 
            return None
        if user.validate_password(identity.get('password')):
            return user.name
        return None

