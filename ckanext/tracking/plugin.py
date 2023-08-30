import ckan.plugins as p

from ckan.plugins import toolkit

class TrackingPlugin(p.SingletonPlugin):

    p.implements(p.IMiddleware)

    def make_middleware(self, app, config):
        return app
