from flask import Flask

from ckan.controllers.flapi import ApiView

app = None
registry = None
translator_obj = None

def register_translator():
    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator
    global registry
    registry=Registry()
    registry.prepare()
    global translator_obj
    translator_obj=MockTranslator()
    registry.register(translator, translator_obj)


def create_app():
    global app
    app = Flask("ckan")
    app.debug = True

    app.before_request_funcs = {
        None: [register_translator]
    }

    ##############################################################################
    # Set up routes
    ##############################################################################
    app.add_url_rule('/action/<func_name>', view_func=ApiView.as_view('api'))

    return app


