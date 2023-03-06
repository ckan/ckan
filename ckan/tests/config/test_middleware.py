# encoding: utf-8

import pytest

from flask import Blueprint

from ckan import plugins as p
from ckan.common import config, _
from ckan.lib.helpers import url_for


class BlueprintPlugin(p.SingletonPlugin):

    p.implements(p.IBlueprint)

    def get_blueprint(self):
        bp1 = Blueprint("bp1", self.__module__)
        bp1.add_url_rule(
            "/simple_url",
            "plugin_view_endpoint",
            lambda: "Hello World, this is served from an extension"
        )
        bp1.add_url_rule(
            "/view_translated",
            "view_translated",
            lambda: _(u"Dataset")
        )

        bp2 = Blueprint("bp2", self.__module__)
        bp2.add_url_rule(
            "/another_simple_url",
            "another_plugin_view_endpoint",
            lambda: "Hello World, this is another view served from an extension"
        )

        return [bp1, bp2]


class MiddlewarePlugin(p.SingletonPlugin):
    p.implements(p.IMiddleware, inherit=True)

    def make_middleware(self, app, config):
        return Middleware(app, config)


class Middleware:
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)


@pytest.fixture
def patched_app(app):
    flask_app = app.flask_app

    def test_view():
        return u"This was served from Flask"

    flask_app.add_url_rule(
        u"/flask_core", view_func=test_view, endpoint=u"flask_core.index"
    )
    return app


def test_flask_core_route_is_served(patched_app):
    res = patched_app.get(u"/")
    assert res.status_code == 200

    res = patched_app.get(u"/flask_core")
    assert res.get_data(as_text=True) == "This was served from Flask"


@pytest.mark.ckan_config(u"SECRET_KEY", u"super_secret_stuff")
def test_secret_key_is_used_if_present(app):
    assert app.flask_app.config[u"SECRET_KEY"] == u"super_secret_stuff"


@pytest.mark.ckan_config(u"SECRET_KEY", None)
def test_beaker_secret_is_used_by_default(app):
    assert (
        app.flask_app.config[u"SECRET_KEY"] == config[u"beaker.session.secret"]
    )


@pytest.mark.ckan_config(u"SECRET_KEY", None)
@pytest.mark.ckan_config(u"beaker.session.secret", None)
def test_no_beaker_secret_crashes(make_app):
    with pytest.raises(RuntimeError):
        make_app()


@pytest.mark.ckan_config(u"ckan.plugins", u"test_blueprint_plugin")
@pytest.mark.usefixtures(u"with_plugins")
def test_all_plugin_blueprints_are_registered(app):
    url = url_for("bp1.plugin_view_endpoint")
    assert url == "/simple_url"
    res = app.get(url, status=200)
    assert "Hello World, this is served from an extension" in res.body

    url = url_for("bp1.view_translated")
    assert url == "/view_translated"
    res = app.get(url, status=200)
    assert "Dataset" in res.body

    url = url_for("bp2.another_plugin_view_endpoint")
    assert url == "/another_simple_url"
    res = app.get(url, status=200)
    assert "Hello World, this is another view served from an extension" in res.body


@pytest.mark.ckan_config("REMEMBER_COOKIE_DURATION", "12345")
def test_flask_config_values_are_parsed(app):
    assert (
        app.flask_app.config["REMEMBER_COOKIE_DURATION"] == 12345
    )


@pytest.mark.ckan_config("WTF_CSRF_SECRET_KEY", None)
def test_no_wtf_secret_falls_back_to_secret_key(app):
    assert (
        app.flask_app.config["WTF_CSRF_SECRET_KEY"] == config.get("beaker.session.secret")
    )
    assert (
        config["WTF_CSRF_SECRET_KEY"] == config.get("beaker.session.secret")
    )


@pytest.mark.ckan_config(u"ckan.plugins", u"test_middleware_plugin")
@pytest.mark.usefixtures(u"with_plugins")
def test_custom_middleware_does_not_break_the_app(app):
    app.get("/", status=200)
