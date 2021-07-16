# -*- coding: utf-8 -*-

import os

import pytest
from six.moves.urllib.parse import urlparse

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.common import config
from ckan.tests import factories


def test_ckan_config_fixture(ckan_config):
    assert tk.asbool(ckan_config["testing"])


def test_ckan_config_do_not_have_some_new_config(ckan_config):
    assert "some.new.config" not in ckan_config


# START-CONFIG-OVERRIDE
@pytest.mark.ckan_config("some.new.config", "exists")
def test_ckan_config_mark(ckan_config):
    assert ckan_config["some.new.config"] == "exists"


# END-CONFIG-OVERRIDE


@pytest.mark.ckan_config("some.new.config", "exists")
@pytest.mark.usefixtures("ckan_config")
def test_ckan_config_mark_without_explicit_config_fixture():
    assert config["some.new.config"] == "exists"


@pytest.mark.ckan_config("ckan.plugins", "stats")
@pytest.mark.usefixtures("with_plugins")
def test_with_plugins_is_able_to_run_with_stats():
    assert plugins.plugin_loaded("stats")


class TestMethodLevelConfig(object):
    """Verify that config overrides work for individual methods.
    """

    @pytest.mark.ckan_config("some.new.config", "exists")
    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config["some.new.config"] == "exists"

    @pytest.mark.ckan_config("some.new.config", "exists again")
    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config["some.new.config"] == "exists again"


@pytest.mark.ckan_config("some.new.config", "exists")
class TestClassLevelConfig(object):

    """Verify that config overrides applied for each method when applied
    per on class level.
    """

    def test_ckan_config_mark_first(self, ckan_config):
        assert ckan_config["some.new.config"] == "exists"

    def test_ckan_config_mark_second(self, ckan_config):
        assert ckan_config["some.new.config"] == "exists"


class TestCreateWithUpload(object):

    def test_create_organization(self, create_with_upload, ckan_config):
        user = factories.User()
        context = {
            "user": user["name"]
        }
        org = create_with_upload(
            b"\0\0\0", "image.png",
            context=context,
            action="organization_create",
            upload_field_name="image_upload",
            name="test-org"
        )
        image_path = os.path.join(
            ckan_config["ckan.storage_path"],
            'storage',
            urlparse(org['image_display_url']).path.lstrip("/")
        )

        assert os.path.isfile(image_path)
        with open(image_path, "rb") as image:
            content = image.read()
            assert content == b"\0\0\0"

    def test_create_resource(self, create_with_upload):
        dataset = factories.Dataset()
        resource = create_with_upload(
            "hello world", "file.txt",
            package_id=dataset['id']
        )
        assert resource["url_type"] == "upload"
        assert resource["format"] == "TXT"
        assert resource["size"] == 11


class TestMigrateDbFor(object):
    @pytest.mark.ckan_config("ckan.plugins", "example_database_migrations")
    @pytest.mark.usefixtures("with_plugins", "clean_db")
    def test_migrations_applied(self, migrate_db_for):
        import ckan.model as model
        has_table = model.Session.bind.has_table
        assert not has_table("example_database_migrations_x")
        assert not has_table("example_database_migrations_y")

        migrate_db_for("example_database_migrations")

        assert has_table("example_database_migrations_x")
        assert has_table("example_database_migrations_y")
