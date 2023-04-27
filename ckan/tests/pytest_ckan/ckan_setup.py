# -*- coding: utf-8 -*-

import ckan.plugins as plugins
from ckan.config.middleware import make_app
from ckan.cli import load_config
from ckan.common import config

# This is a test Flask request context to be used internally.
# Do not use it!
_tests_test_request_context = None

# Initial config snapshot that is used to restore config object before each
# test. This allows us to keep tests independent while we are using global
# config object.
_config = config.copy()


def pytest_addoption(parser):
    """Allow using custom config file during tests.

    Catch the exception raised by pytest if  the ``--ckan-ini`` option was
    already added by the external pytest-ckan package
    """
    try:
        parser.addoption(u"--ckan-ini", action=u"store")
    except ValueError as e:
        if str(e) == 'option names {\'--ckan-ini\'} already added':
            pass
        else:
            raise


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

    # Create the snapshot of the initial configuration
    global _config
    _config = config.copy()


def pytest_runtestloop(session):
    """When all the tests collected, extra plugin may be enabled because python
    interpreter visits their files.

    Make sure only configured plugins are active when test loop starts.
    """
    plugins.load_all()


def pytest_runtest_setup(item):
    """Automatically apply `ckan_config` fixture if test has `ckan_config`
    mark.

    `ckan_config` mark itself does nothing(as any mark). All actual
    config changes performed inside `ckan_config` fixture. So let's
    implicitly use `ckan_config` fixture inside any test that patches
    config object. This will save us from adding
    `@mark.usefixtures("ckan_config")` every time.

    """
    # Restore configuration from the snapshot, removing all customization that
    # were done during previous tests.  Note, it is not related to
    # `ckan_config` fixture, which restores config object itself. This is
    # needed because such modules as `ckan.lib.app_globals` can mutate global
    # config object. Potentially can be removed, when the logic behind
    # `app_globals` stops modifying global config object.
    config.clear()
    config.update(_config)

    custom_config = [
        mark.args for mark in item.iter_markers(name=u"ckan_config")
    ]

    if custom_config:
        item.fixturenames.append(u"ckan_config")
