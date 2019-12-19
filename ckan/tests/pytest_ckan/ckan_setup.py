# -*- coding: utf-8 -*-

from ckan.lib.cli import load_config


def pytest_addoption(parser):
    """Allow using custom config file during tests.
    """
    parser.addoption(u"--ckan-ini", action=u"store")


def pytest_sessionstart(session):
    """Initialize CKAN environment.
    """
    load_config(session.config.option.ckan_ini)


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
