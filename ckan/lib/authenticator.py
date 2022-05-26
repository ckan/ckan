# encoding: utf-8

import logging
import ckan.plugins as plugins
from typing import Any, Mapping, Optional

from ckan.model import User
from . import signals

log = logging.getLogger(__name__)


def default_authenticate(identity: 'Mapping[str, Any]') -> Optional["User"]:
    if not ('login' in identity and 'password' in identity):
        return None

    login = identity['login']
    user = User.by_name(login)
    if not user:
        user = User.by_email(login)

    if user is None:
        log.debug('Login failed - username or email %r not found', login)
    elif not user.is_active():
        log.debug('Login as %r failed - user isn\'t active', login)
    elif not user.validate_password(identity['password']):
        log.debug('Login as %r failed - password not valid', login)
    else:
        signals.successful_login.send(user.name)
        return user
    signals.failed_login.send(login)
    return None


def ckan_authenticator(identity: 'Mapping[str, Any]') -> Optional["User"]:
    """Allows extensions that have implemented
    `IAuthenticator.authenticate()` to hook into the CKAN authentication
    process with a custom implementation.

    Falls to default `UsernamePasswordAuthenticator` if no plugins are
    defined.
    """
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        response = item.authenticate(identity)
        if response:
            return response
    return default_authenticate(identity)
