from repoze.who._compat import CONTENT_TYPE
from repoze.who._compat import REQUEST_METHOD
from repoze.who._compat import USER_AGENT

from zope.interface import directlyProvides
from repoze.who.interfaces import IRequestClassifier
from repoze.who.interfaces import IChallengeDecider

_DAV_METHODS = (
    'OPTIONS',
    'PROPFIND',
    'PROPPATCH',
    'MKCOL',
    'LOCK',
    'UNLOCK',
    'TRACE',
    'DELETE',
    'COPY',
    'MOVE'
    )

_DAV_USERAGENTS = (
    'Microsoft Data Access Internet Publishing Provider',
    'WebDrive',
    'Zope External Editor',
    'WebDAVFS',
    'Goliath',
    'neon',
    'davlib',
    'wsAPI',
    'Microsoft-WebDAV'
    )

def default_request_classifier(environ):
    """Return one of the following classifiers:

    'dav':  the request comes from a WebDAV agent.

    'xmlpost':  the request is a POST of XML data.

    'browser':  the request comes from a normal browser (default).
    """
    request_method = REQUEST_METHOD(environ)
    if request_method in _DAV_METHODS:
        return 'dav'
    useragent = USER_AGENT(environ)
    if useragent:
        for agent in _DAV_USERAGENTS:
            if useragent.find(agent) != -1:
                return 'dav'
    if request_method == 'POST':
        if CONTENT_TYPE(environ).lower().startswith('text/xml'):
            return 'xmlpost'
    return 'browser'
directlyProvides(default_request_classifier, IRequestClassifier)

def default_challenge_decider(environ, status, headers):
    return status.startswith('401 ')
directlyProvides(default_challenge_decider, IChallengeDecider)

def passthrough_challenge_decider(environ, status, headers):
    """ Don't challenge for pre-challenged responses.

    o Assume responsese with 'WWW-Authenticate' or an HTML content type
      are pre-challenged.
    """
    if not status.startswith('401 '):
        return False
    h_dict = dict(headers)
    if 'WWW-Authenticate' in h_dict:
        return False
    ct = h_dict.get('Content-Type')
    if ct is not None:
        return not ct.startswith('text/html')
    return True
directlyProvides(passthrough_challenge_decider, IChallengeDecider)
