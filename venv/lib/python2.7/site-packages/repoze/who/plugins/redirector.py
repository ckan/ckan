from webob.exc import HTTPFound
from zope.interface import implementer

from repoze.who.interfaces import IChallenger
from repoze.who._compat import construct_url
from repoze.who._compat import header_value
from repoze.who._compat import parse_qs
from repoze.who._compat import u
from repoze.who._compat import urlencode
from repoze.who._compat import urlparse
from repoze.who._compat import urlunparse

@implementer(IChallenger)
class RedirectorPlugin(object):
    """ Plugin for issuing challenges as redirects to a configured URL.

    o If the ``reason_param`` option is configured, and the application has
      supplied an ``X-Authorization-Failure-Reason`` header, the plugin
      includes that reason in the query string of the redirected URL.
    """

    def __init__(self,
                 login_url,
                 came_from_param='came_from',
                 reason_param='reason',
                 reason_header='X-Authorization-Failure-Reason',
                ):
        self.login_url = login_url
        self.came_from_param = came_from_param
        if ((reason_param is None and reason_header is not None) or
            (reason_param is not None and reason_header is None)):
            raise ValueError(
                "Must supply both 'reason_header' and 'reason_param', "
                "or neither one.")
        self.reason_param = reason_param
        self.reason_header = reason_header
        self._login_url_parts = list(urlparse(login_url))

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        if self.reason_param is not None or self.came_from_param is not None:
            url_parts = self._login_url_parts[:]
            query = url_parts[4]
            query_elements = parse_qs(query)
            if self.reason_param is not None:
                reason = header_value(app_headers, self.reason_header)
                if reason:
                    query_elements[self.reason_param] = reason
            if self.came_from_param is not None:
                query_elements[self.came_from_param] = construct_url(environ)
            url_parts[4] = urlencode(query_elements, doseq=True)
            login_url = urlunparse(url_parts)
        else:
            login_url = self.login_url
        headers = [('Location', login_url)] + forget_headers
        cookies = [(h,v) for (h,v) in app_headers if h.lower() == 'set-cookie']
        headers += cookies
        return HTTPFound(headers=headers)

def make_plugin(login_url,
                came_from_param=None,
                reason_param=None,
                reason_header=None,
               ):
    if login_url in (u(''), b'', None):
        raise ValueError("No 'login_url'")
    if reason_header is not None and reason_param is None:
        raise Exception("Can't set 'reason_header' without 'reason_param'.")

    if reason_header is None and reason_param is not None:
        reason_header='X-Authorization-Failure-Reason'

    return RedirectorPlugin(login_url,
                            came_from_param=came_from_param,
                            reason_param=reason_param,
                            reason_header=reason_header,
                           )
