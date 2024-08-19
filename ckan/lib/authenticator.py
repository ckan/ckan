from __future__ import annotations

import logging
from ckan import model, plugins
from typing import Any

from ckan.common import g, request
from ckan.lib import captcha
from ckan.model import User
from . import signals

log = logging.getLogger(__name__)


def default_authenticate(
        identity: dict[str, Any]
) -> model.User | model.AnonymousUser | None:
    if not ('login' in identity and 'password' in identity):
        return None

    login = identity['login']
    user_obj = User.by_name(login)
    if not user_obj:
        user_obj = User.by_email(login)

    if user_obj is None:
        log.debug('Login failed - username or email %r not found', login)
    elif not user_obj.is_active:
        log.debug('Login as %r failed - user isn\'t active', login)
    elif not user_obj.validate_password(identity['password']):
        log.debug('Login as %r failed - password not valid', login)
    else:
        check_captcha = identity.get('check_captcha', True)
        if check_captcha and g.recaptcha_publickey:
            # Check for a valid reCAPTCHA response
            try:
                client_ip_address = request.remote_addr or 'Unknown IP Address'
                captcha.check_recaptcha_v2_base(
                    client_ip_address,
                    request.form.get(u'g-recaptcha-response', '')
                )
                return user_obj
            except captcha.CaptchaError:
                log.warning('Login as %r failed - failed reCAPTCHA', login)
                request.environ[u'captchaFailed'] = True
        else:
            return user_obj
    signals.failed_login.send(login)
    return None


def ckan_authenticator(
        identity: dict[str, Any]
) -> model.User | model.AnonymousUser | None:
    """Allows extensions that have implemented
    `IAuthenticator.authenticate()` to hook into the CKAN authentication
    process with a custom implementation.

    Falls to `default_authenticate()` if no plugins are
    defined.
    """
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        user_obj = item.authenticate(identity)
        if user_obj:
            return user_obj
    return default_authenticate(identity)
