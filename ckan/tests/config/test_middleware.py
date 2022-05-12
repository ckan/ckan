# encoding: utf-8

import pytest
import six
from flask import Blueprint

import ckan.plugins as p
from ckan.common import config, _


class MockRoutingPlugin(p.SingletonPlugin):

    p.implements(p.IBlueprint)

    def get_blueprint(self):
        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)

        blueprint.add_url_rule(
            u"/simple_flask", u"flask_plugin_view", flask_plugin_view
        )

        blueprint.add_url_rule(
            u"/flask_translated", u"flask_translated", flask_translated_view
        )

        return blueprint


def flask_plugin_view():
    return u"Hello World, this is served from a Flask extension"


def flask_translated_view():
    return _(u"Dataset")


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
    assert six.ensure_text(res.data) == u"This was served from Flask"


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
    # TODO: When Pylons is finally removed, we should test for
    # RuntimeError instead (thrown on `make_flask_stack`)
    with pytest.raises(RuntimeError):
        make_app()
