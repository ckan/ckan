# -*- coding: utf-8 -*-

import os

import pytest
import six
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


@pytest.mark.ckan_config(u"ckan.site_url", u"https://example.org")
@pytest.mark.usefixtures(u"with_request_context")
def test_existing_ckan_config_mark_with_test_request(ckan_config):
    assert ckan_config[u"ckan.site_url"] == u"https://example.org"


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
        some_png = """
        89 50 4E 47 0D 0A 1A 0A 00 00 00 0D 49 48 44 52
        00 00 00 01 00 00 00 01 08 02 00 00 00 90 77 53
        DE 00 00 00 0C 49 44 41 54 08 D7 63 F8 CF C0 00
        00 03 01 01 00 18 DD 8D B0 00 00 00 00 49 45 4E
        44 AE 42 60 82"""
        some_png = some_png.replace(u' ', u'').replace(u'\n', u'')
        some_png_bytes = bytes(bytearray.fromhex(some_png))

        org = create_with_upload(
            some_png_bytes, u"image.png",
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
            # PNG signature
            if six.PY3:
                assert content.hex()[:16].upper() == u'89504E470D0A1A0A'
            else:
                assert content.encode(u"hex")[:16].upper() == u'89504E470D0A1A0A'

    def test_create_resource(self, create_with_upload):
        dataset = factories.Dataset()
        resource = create_with_upload(
            u"hello world", u"file.txt",
            package_id=dataset[u'id']
        )
        assert resource[u"url_type"] == u"upload"
        assert resource[u"format"] == u"TXT"
        assert resource[u"size"] == 11


class TestMigrateDbFor(object):
    @pytest.mark.ckan_config(u"ckan.plugins", u"example_database_migrations")
    @pytest.mark.usefixtures(u"with_plugins", u"clean_db")
    def test_migrations_applied(self, migrate_db_for):
        import ckan.model as model
        has_table = model.Session.bind.has_table
        assert not has_table(u"example_database_migrations_x")
        assert not has_table(u"example_database_migrations_y")

        migrate_db_for(u"example_database_migrations")

        assert has_table(u"example_database_migrations_x")
        assert has_table(u"example_database_migrations_y")
