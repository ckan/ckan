from flask import Flask

from ckan.controllers.flapi import ApiView

app = None
registry = None
translator_obj = None

def fake_pylons():
    import pylons
    from pylons.util import ContextObj, PylonsContext

    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator

    global registry
    global translator_obj

    c = pylons.util.AttribSafeContextObj()

    registry=Registry()
    registry.prepare()

    translator_obj=MockTranslator()

    registry.register(translator, translator_obj)
    registry.register(pylons.c, c)


def unfake_pylons(response):
    import pylons
    pylons.tmpl_context._pop_object()
    return response


def create_app():
    global app
    app = Flask("ckan")
    app.debug = True

    app.before_request_funcs = {
        None: [fake_pylons]
    }
    app.after_request_funcs = {
        None: [unfake_pylons]
    }

    ##############################################################################
    # Set up routes
    ##############################################################################
    app.add_url_rule('/api/3/action/<func_name>', view_func=ApiView.as_view('api'))

    return app


