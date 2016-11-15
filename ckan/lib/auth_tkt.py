# encoding: utf-8

import logging
import math
import os

from ckan.common import config
from repoze.who.plugins import auth_tkt as repoze_auth_tkt

_bool = repoze_auth_tkt._bool

log = logging.getLogger(__name__)


class CkanAuthTktCookiePlugin(repoze_auth_tkt.AuthTktCookiePlugin):

    def __init__(self, httponly, *args, **kwargs):
        super(CkanAuthTktCookiePlugin, self).__init__(*args, **kwargs)
        self.httponly = httponly

    def _get_cookies(self, *args, **kwargs):
        '''
        Override method in superclass to ensure HttpOnly is set appropriately.
        '''
        super_cookies = super(CkanAuthTktCookiePlugin, self). \
            _get_cookies(*args, **kwargs)

        cookies = []
        for k, v in super_cookies:
            replace_with = '; HttpOnly' if self.httponly else ''
            v = v.replace('; HttpOnly', '') + replace_with
            cookies.append((k, v))

        return cookies


def make_plugin(secret=None,
                secretfile=None,
                cookie_name='auth_tkt',
                secure=False,
                include_ip=False,
                timeout=None,
                reissue_time=None,
                userid_checker=None):
    from repoze.who.utils import resolveDotted

    # ckan specifics:
    # Get secret from beaker setting if necessary
    if secret is None or secret == 'somesecret':
        secret = config['beaker.session.secret']
    # Session timeout and reissue time for auth cookie
    if timeout is None and config.get('who.timeout'):
        timeout = config.get('who.timeout')
    if reissue_time is None and config.get('who.reissue_time'):
        reissue_time = config.get('who.reissue_time')
    if timeout is not None and reissue_time is None:
        reissue_time = int(math.ceil(int(timeout) * 0.1))
    # Set httponly based on config value. Default is True
    httponly = config.get('who.httponly', True)
    # Set secure based on config value. Default is False
    secure = config.get('who.secure', False)

    # back to repoze boilerplate
    if (secret is None and secretfile is None):
        raise ValueError("One of 'secret' or 'secretfile' must not be None.")
    if (secret is not None and secretfile is not None):
        raise ValueError("Specify only one of 'secret' or 'secretfile'.")
    if secretfile:
        secretfile = os.path.abspath(os.path.expanduser(secretfile))
        if not os.path.exists(secretfile):
            raise ValueError("No such 'secretfile': %s" % secretfile)
        secret = open(secretfile).read().strip()
    if timeout:
        timeout = int(timeout)
    if reissue_time:
        reissue_time = int(reissue_time)
    if userid_checker is not None:
        userid_checker = resolveDotted(userid_checker)
    plugin = CkanAuthTktCookiePlugin(_bool(httponly),
                                     secret,
                                     cookie_name,
                                     _bool(secure),
                                     _bool(include_ip),
                                     timeout,
                                     reissue_time,
                                     userid_checker)
    return plugin
