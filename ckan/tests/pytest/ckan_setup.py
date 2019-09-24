# -*- coding: utf-8 -*-

from ckan.lib.cli import load_config


def pytest_addoption(parser):
    parser.addoption(u"--ckan-ini", action=u"store")


def pytest_sessionstart(session):
    load_config(session.config.option.ckan_ini)
