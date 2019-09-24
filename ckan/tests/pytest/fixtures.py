# -*- coding: utf-8 -*-
import pytest
from ckan.tests.helpers import _get_test_app
from ckan.common import config


@pytest.fixture
def ckan_config(request, monkeypatch):
    for mark in request.node.own_markers:
        if mark.name == 'ckan_config':
            monkeypatch.setitem(config, *mark.args)
    return config


@pytest.fixture
def app(ckan_config):
    return _get_test_app()
