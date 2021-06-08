# encoding: utf-8

import logging
import math
import os

import six

try:
    from http.cookies import SimpleCookie
except ImportError:
    from Cookie import SimpleCookie

from ckan.common import config
from repoze.who.plugins import auth_tkt as repoze_auth_tkt

_bool = repoze_auth_tkt._bool

log = logging.getLogger(__name__)

# With `unicode` decoder users that were logged in on CKAN+py2 will
# get 500 on CKAN+py3 error because of to utf8_decode attempts applied
# to str, while bytes-like object expected.
_ckan_userid_type_decoders = dict(
    repoze_auth_tkt.AuthTktCookiePlugin.userid_type_decoders
)
if six.PY3:
    _ckan_userid_type_decoders.pop('unicode')


class CkanAuthTktCookiePlugin(repoze_auth_tkt.AuthTktCookiePlugin):

    userid_type_decoders = _ckan_userid_type_decoders

    def __init__(self, httponly, samesite, *args, **kwargs):
        super(CkanAuthTktCookiePlugin, self).__init__(*args, **kwargs)
        self.httponly = httponly
        self.samesite = samesite

    def _get_cookies(self, *args, **kwargs):
        u'''
        Override method in superclass to ensure HttpOnly is set appropriately.
        '''
        super_cookies = super(CkanAuthTktCookiePlugin, self). \
            _get_cookies(*args, **kwargs)

        cookies = []
        for k, v in super_cookies:
            cookie = SimpleCookie(str(v))
            morsel = list(cookie.values())[0]
            # SameSite was only added on Python 3.8
            morsel._reserved['samesite'] = 'SameSite'
            # Keep old case as it's the one used in tests, it should make no
            # difference in the browser
            morsel._reserved['httponly'] = 'HttpOnly'
            morsel._reserved['secure'] = 'Secure'

            if self.httponly:
                cookie[self.cookie_name]['HttpOnly'] = True

            if self.samesite == 'none':
                cookie[self.cookie_name]['SameSite'] = 'None'
            elif self.samesite == 'strict':
                cookie[self.cookie_name]['SameSite'] = 'Strict'
            else:
                cookie[self.cookie_name]['SameSite'] = 'Lax'

            cookies.append((k, cookie.output().replace('Set-Cookie: ', '')))

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
    if secret is None or secret == u'somesecret':
        secret = config[u'beaker.session.secret']
    # Session timeout and reissue time for auth cookie
    if timeout is None and config.get(u'who.timeout'):
        timeout = config.get(u'who.timeout')
    if reissue_time is None and config.get(u'who.reissue_time'):
        reissue_time = config.get(u'who.reissue_time')
    if timeout is not None and reissue_time is None:
        reissue_time = int(math.ceil(int(timeout) * 0.1))
    # Set httponly based on config value. Default is True
    httponly = _bool(config.get(u'who.httponly', True))
    # Set secure based on config value. Default is False
    secure = _bool(config.get(u'who.secure', False))
    # Set samesite based on config value. Default is lax
    samesite = config.get(u'who.samesite', 'lax').lower()
    if samesite == 'none' and not secure:
        raise ValueError(
            'SameSite=None requires the Secure attribute,'
            'please set who.secure=True')

    # back to repoze boilerplate
    if (secret is None and secretfile is None):
        raise ValueError(u"One of 'secret' or 'secretfile' must not be None.")
    if (secret is not None and secretfile is not None):
        raise ValueError(u"Specify only one of 'secret' or 'secretfile'.")
    if secretfile:
        secretfile = os.path.abspath(os.path.expanduser(secretfile))
        if not os.path.exists(secretfile):
            raise ValueError(u"No such 'secretfile': %s" % secretfile)
        secret = open(secretfile).read().strip()
    if timeout:
        timeout = int(timeout)
    if reissue_time:
        reissue_time = int(reissue_time)
    if userid_checker is not None:
        userid_checker = resolveDotted(userid_checker)
    plugin = CkanAuthTktCookiePlugin(httponly,
                                     samesite,
                                     secret,
                                     cookie_name,
                                     secure,
                                     _bool(include_ip),
                                     timeout,
                                     reissue_time,
                                     userid_checker)
    return plugin
