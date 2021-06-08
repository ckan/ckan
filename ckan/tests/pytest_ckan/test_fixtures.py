# -*- coding: utf-8 -*-

import os

import pytest
from six.moves.urllib.parse import urlparse

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.common import config
from ckan.tests import factories


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


class TestMethodLevelConfig(object):
    """Verify that config overrides work for individual methods.
    """

    @pytest.mark.ckan_config(u"some.new.config", u"exists")
    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"

    @pytest.mark.ckan_config(u"some.new.config", u"exists again")
    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists again"


@pytest.mark.ckan_config(u"some.new.config", u"exists")
class TestClassLevelConfig(object):

    """Verify that config overrides applied for each method when applied
    per on class level.
    """

    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"

    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config[u"some.new.config"] == u"exists"


class TestCreateWithUpload(object):

    def test_create_organization(self, create_with_upload, ckan_config):
        user = factories.User()
        context = {
            u"user": user["name"]
        }
        org = create_with_upload(
            b"\0\0\0", u"image.png",
            context=context,
            action=u"organization_create",
            upload_field_name=u"image_upload",
            name=u"test-org"
        )
        image_path = os.path.join(
            ckan_config[u"ckan.storage_path"],
            u'storage',
            urlparse(org[u'image_display_url']).path.lstrip(u"/")
        )

        assert os.path.isfile(image_path)
        with open(image_path, u"rb") as image:
            content = image.read()
            assert content == b"\0\0\0"

    def test_create_resource(self, create_with_upload):
        dataset = factories.Dataset()
        resource = create_with_upload(
            u"hello world", u"file.txt",
            package_id=dataset[u'id']
        )
        assert resource[u"url_type"] == u"upload"
        assert resource[u"format"] == u"TXT"
        assert resource[u"size"] == 11
