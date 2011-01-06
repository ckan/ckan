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
                # TODO: Implement a mask to ask for an alternative user 
                # name instead of just using the OpenID identifier. 
                name = identity.get('repoze.who.plugins.openid.nickname')
                if not name or not len(name.strip()) \
                    or not User.VALID_NAME.match(name):
                    name = openid
                if User.by_name(name):
                    name = openid
                user = User(openid=openid, name=name,
                        fullname=identity.get('repoze.who.plugins.openid.fullname'),
                        email=identity.get('repoze.who.plugins.openid.email'))
                Session.add(user)
                Session.commit()
                Session.remove()
            return user.name
        return None
    


