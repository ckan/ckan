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
    custom_config = [mark.args for mark in item.iter_markers(name=u"ckan_config")]
    if custom_config:
        item.fixturenames.append(u"ckan_config")
