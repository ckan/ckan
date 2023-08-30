import ckan.plugins as p

from ckan.plugins import toolkit

from .cli.tracking import tracking
from .middleware import TrackingMiddleware



class TrackingPlugin(p.SingletonPlugin):

    p.implements(p.IClick)
    p.implements(p.IConfigurer)
    p.implements(p.IMiddleware)

    # IClick
    def get_commands(self):
        return [tracking]

    # IConfigurer
    def update_config(self, config):
        toolkit.add_resource("assets", "tracking")
        toolkit.add_template_directory(config, "templates")


    # IMiddleware
    def make_middleware(self, app, config):
        app = TrackingMiddleware(app, config)
        return app


    def make_error_log_middleware(self, app, config):
        return app
