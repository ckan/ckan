import ckan.plugins as p

from ckan.plugins import toolkit

from .middleware import TrackingMiddleware


class TrackingPlugin(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IMiddleware)


    def update_config(self, config):
        toolkit.add_resource("assets", "tracking")
        toolkit.add_template_directory(config, "templates")


    def make_middleware(self, app, config):
        app = TrackingMiddleware(app, config)
        return app


    def make_error_log_middleware(self, app, config):
        return app
