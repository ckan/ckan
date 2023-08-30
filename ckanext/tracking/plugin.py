import ckan.plugins as p

from ckan.plugins import toolkit

from .middleware import TrackingMiddleware

class TrackingPlugin(p.SingletonPlugin):

    p.implements(p.IMiddleware)

    def make_middleware(self, app, config):
        app = TrackingMiddleware(app, config)
        return app

    def make_error_log_middleware(self, app, config):
        return app
