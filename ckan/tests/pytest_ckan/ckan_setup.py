# -*- coding: utf-8 -*-

import six

from ckan.config.middleware import make_app
from ckan.cli import load_config

# This is a test Flask request context to be used internally.
# Do not use it!
_tests_test_request_context = None


def pytest_addoption(parser):
    """Allow using custom config file during tests.
    """
    parser.addoption(u"--ckan-ini", action=u"store")


def pytest_sessionstart(session):
    """Initialize CKAN environment.
    """
    conf = load_config(session.config.option.ckan_ini)
    # Set this internal test request context with the configured environment so
    # it can be used when calling url_for from the cli.
    global _tests_test_request_context

    app = make_app(conf)
    try:
        flask_app = app.apps['flask_app']._wsgi_app
    except AttributeError:
        flask_app = app._wsgi_app
    _tests_test_request_context = flask_app.test_request_context()


def pytest_runtest_setup(item):
    """Automatically apply `ckan_config` fixture if test has `ckan_config`
    mark.

    `ckan_config` mark itself does nothing(as any mark). All actual
    config changes performed inside `ckan_config` fixture. So let's
    implicitely use `ckan_config` fixture inside any test that patches
    config object. This will save us from adding
    `@mark.usefixtures("ckan_config")` every time.

    """
    custom_config = [
        mark.args for mark in item.iter_markers(name=u"ckan_config")
    ]

    if custom_config:
        item.fixturenames.append(u"ckan_config")
