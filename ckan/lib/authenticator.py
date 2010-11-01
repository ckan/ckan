from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

from ckan.model import User, Session

class OpenIDAuthenticator(object):
    implements(IAuthenticator)
    
    def authenticate(self, environ, identity):
        if 'repoze.who.plugins.openid.userid' in identity:
            openid = identity.get('repoze.who.plugins.openid.userid')
            user = User.by_openid(openid)
            # TODO: Validate nickname from OpenID 
            if user is None:
                user = User(openid = openid,
                        name = identity.get('repoze.who.plugins.openid.nickname', openid),
                        fullname = identity.get('repoze.who.plugins.openid.fullname'),
                        email = identity.get('repoze.who.plugins.openid.email'))
                Session.add(user)
                Session.commit()
                Session.remove()
            return user.name
        return None
    


