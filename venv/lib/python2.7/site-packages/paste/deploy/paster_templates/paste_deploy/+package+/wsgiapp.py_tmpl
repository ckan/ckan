from paste.deploy.config import ConfigMiddleware

import sampleapp


def make_app(
    global_conf,
    # Optional and required configuration parameters
    # can go here, or just **kw; greeting is required:
    greeting,
    **kw):
    # This is a WSGI application:
    app = sampleapp.application
    # Here we merge all the keys into one configuration
    # dictionary; you don't have to do this, but this
    # can be convenient later to add ad hoc configuration:
    conf = global_conf.copy()
    conf.update(kw)
    conf['greeting'] = greeting
    # ConfigMiddleware means that paste.deploy.CONFIG will,
    # during this request (threadsafe) represent the
    # configuration dictionary we set up:
    app = ConfigMiddleware(app, conf)
    return app
