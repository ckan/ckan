# -*- coding: utf-8 -*-

import pytest

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.common import config


def test_ckan_config_fixture(ckan_config):
    assert tk.asbool(ckan_config[u"testing"])


def test_ckan_config_do_not_have_some_new_config(ckan_config):
    assert u"some.new.config" not in ckan_config


# START-CONFIG-OVERRIDE
@pytest.mark.ckan_config(u"some.new.config", u"exists")
def test_ckan_config_mark(ckan_config):
    assert ckan_config[u"some.new.config"] == u"exists"


# END-CONFIG-OVERRIDE


@pytest.mark.ckan_config(u"some.new.config", u"exists")
@pytest.mark.usefixtures(u"ckan_config")
def test_ckan_config_mark_without_explicit_config_fixture():
    assert config[u"some.new.config"] == u"exists"


@pytest.mark.ckan_config(u"ckan.plugins", u"stats")
@pytest.mark.usefixtures(u"with_plugins")
def test_with_plugins_is_able_to_run_with_stats():
    assert plugins.plugin_loaded(u"stats")


class TestMethodLevelConfig:
    """Verify that config overrides work for individual methods.
    """

    @pytest.mark.ckan_config(u"some.new.config", u"exists")
    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"

    @pytest.mark.ckan_config(u"some.new.config", u"exists again")
    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists again"


@pytest.mark.ckan_config(u"some.new.config", u"exists")
class TestClassLevelConfig:
    """Verify that config overrides applied for each method when applied
    per on class level.
    """

    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"

    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"
