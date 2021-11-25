# encoding: utf-8

import logging

from ckan.model import User
from ckan.plugins import toolkit as tk
# from zope.interface import implementer
# from repoze.who.interfaces import IAuthenticator

log = logging.getLogger(__name__)

# @implementer(IAuthenticator)
class UsernamePasswordAuthenticator(object):

    def authenticate(self, identity):
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
            tk.signals.successful_login.send(user.name)
            return user.name
        tk.signals.failed_login.send(login)
        return None
