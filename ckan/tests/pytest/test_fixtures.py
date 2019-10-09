# -*- coding: utf-8 -*-

import pytest

import ckan.plugins.toolkit as tk
from ckan.common import config


def test_ckan_config_fixture(ckan_config):
    assert tk.asbool(ckan_config[u'testing'])


def test_ckan_config_do_not_have_some_new_config(ckan_config):
    assert u'some.new.config' not in ckan_config


@pytest.mark.ckan_config(u'some.new.config', u'exists')
def test_ckan_config_mark(ckan_config):
    assert u'exists' == ckan_config[u'some.new.config']


@pytest.mark.ckan_config(u'some.new.config', u'exists')
@pytest.mark.usefixtures(u'ckan_config')
def test_ckan_config_mark_without_explicit_config_fixture():
    assert u'exists' == config[u'some.new.config']
