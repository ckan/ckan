import os

from pylons import config
from repoze.who.plugins import auth_tkt as repoze_auth_tkt

_bool = repoze_auth_tkt._bool

import logging
log = logging.getLogger(__name__)


class CkanAuthTktCookiePlugin(repoze_auth_tkt.AuthTktCookiePlugin):

    def __init__(self, httponly, *args, **kwargs):
        super(CkanAuthTktCookiePlugin, self).__init__(*args, **kwargs)
        self.httponly = httponly

    def _ensure_httponly_for_cookies(self, cookies):
        '''
        Take a list of cookie tuples items and ensure HttpOnly is set
        correctly.
        '''
        # change tuples to lists
        cookie_list = [list(c) for c in cookies]
        # ensure httponly is set correctly for each cookie
        for cookie in cookie_list:
            cookie[1] = _set_substring(cookie[1], '; HttpOnly', self.httponly)
        # change lists back to tuples and return
        return [tuple(c) for c in cookie_list]

    def _get_cookies(self, *args, **kwargs):
        '''
        Override method in superclass to ensure HttpOnly is set appropriately.
        '''
        super_cookies = super(CkanAuthTktCookiePlugin, self). \
            _get_cookies(*args, **kwargs)

        cookies = self._ensure_httponly_for_cookies(super_cookies)

        return cookies


def _set_substring(value, substring, presence=True):
    '''
    Ensure presence/absence of substring in value.

    If presence is True, ensure value contains substring. Append substring to
    value if absent.

    If presence is False, ensure value does not contain substring. Remove
    substring from value is present.
    '''
    has_substring = (substring in value)
    if has_substring and not presence:
        # remove substring
        value = value.replace(substring, '')
    elif not has_substring and presence:
        # add substring
        value += substring
    return value


def make_plugin(httponly=True,
                secret=None,
                secretfile=None,
                cookie_name='auth_tkt',
                secure=False,
                include_ip=False,
                timeout=None,
                reissue_time=None,
                userid_checker=None):
    from repoze.who.utils import resolveDotted

    # ckan specific: get secret from beaker setting if necessary
    if secret is None or secret == 'somesecret':
        secret = config['beaker.session.secret']

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
    plugin = CkanAuthTktCookiePlugin(httponly,
                                     secret,
                                     cookie_name,
                                     _bool(secure),
                                     _bool(include_ip),
                                     timeout,
                                     reissue_time,
                                     userid_checker)
    return plugin
