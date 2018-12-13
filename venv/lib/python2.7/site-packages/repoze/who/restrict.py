# Authorization middleware
from pkg_resources import EntryPoint

from repoze.who._compat import STRING_TYPES

def authenticated_predicate():
    def _predicate(environ):
        return 'REMOTE_USER' in environ or 'repoze.who.identity' in environ
    return _predicate

class PredicateRestriction:

    def __init__(self, app, predicate, enabled=True, **kw):
        self.app = app
        self.enabled = enabled
        options = kw.copy()
        self.predicate = predicate(**options)

    def __call__(self, environ, start_response):
        if self.enabled:
            if not self.predicate(environ):
                start_response('401 Unauthorized', [])
                return []
        return self.app(environ, start_response)

def make_authenticated_restriction(app, global_config, enabled=True):
    return PredicateRestriction(app, authenticated_predicate, enabled)

def make_predicate_restriction(app, global_config,
                               predicate, enabled=True, **kw):
    if isinstance(predicate, STRING_TYPES):
        predicate = EntryPoint.parse('x=%s' % predicate).resolve()
    return PredicateRestriction(app, predicate, enabled, **kw)
