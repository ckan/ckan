import logging

from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

from ckan.model import User, Session

log = logging.getLogger(__name__)

class OpenIDAuthenticator(object):
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        if 'repoze.who.plugins.openid.userid' in identity:
            openid = identity['repoze.who.plugins.openid.userid']
            user = User.by_openid(openid)
            if user is None or not user.is_active():
                return None
            else:
                return user.name
        return None


class UsernamePasswordAuthenticator(object):
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        if not ('login' in identity and 'password' in identity):
            return None

        login = identity['login']
        user = User.by_name(login)

        if user is None:
            log.debug('Login failed - username %r not found', login)
        elif not user.is_active():
            log.debug('Login as %r failed - user isn\'t active', login)
        elif not user.validate_password(identity['password']):
            log.debug('Login as %r failed - password not valid', login)
        else:
            return user.name

        return None

