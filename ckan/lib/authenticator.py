# encoding: utf-8

import logging

from zope.interface import implements
from repoze.who.interfaces import IAuthenticator

from ckan.model import User

log = logging.getLogger(__name__)


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

class BeakerRedisAuth(object):
    implements(IAuthenticator)

    def authenticate(self, environ, identity):
        # At this stage, the identity has already been validated from the cookie
        # and redis (use_beaker middleware). We simply return the user id
        # from the identity object if it's there, or None if the user's
        # identity is not verified.
        return identity.get('repoze.who.userid', None)
