# -*- coding: utf-8 -*-

import os

import pytest
from urllib.parse import urlparse

import ckan.plugins as plugins
from ckan.common import config, asbool
from ckan.tests import factories
from ckan.lib.redis import connect_to_redis


def test_ckan_config_fixture(ckan_config):
    assert asbool(ckan_config[u"testing"])


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


@pytest.mark.ckan_config("ckan.site_url", "https://example.org")
@pytest.mark.usefixtures("with_request_context")
def test_existing_ckan_config_mark_with_test_request(ckan_config):
    assert ckan_config["ckan.site_url"] == "https://example.org"


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

    def test_create_organization(self, create_with_upload, ckan_config, faker):
        user = factories.User()
        context = {
            u"user": user["name"]
        }
        org = create_with_upload(
            faker.image(), u"image.png",
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
            assert content.hex()[:16].upper() == '89504E470D0A1A0A'

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


@pytest.mark.usefixtures("non_clean_db")
def test_non_clean_db_does_not_fail(package_factory):
    assert package_factory()


class TestRedisFixtures:

    @pytest.fixture()
    def add_redis_record(self, redis, faker):
        """Create a random record in Redis."""
        redis.set(faker.word(), faker.word())

    @pytest.fixture()
    def redis(self):
        """Return Redis client."""
        return connect_to_redis()

    @pytest.mark.usefixtures("add_redis_record", "clean_redis")
    def test_clean_redis_after_adding_record(self, redis):
        """clean_redis fixture removes everything from redis."""
        assert redis.keys("*") == []

    @pytest.mark.usefixtures("clean_redis", "add_redis_record")
    def test_clean_redis_before_adding_record(self, redis):
        """It's possible to add data to redis after cleaning."""
        assert len(redis.keys("*")) == 1

    def test_reset_redis(self, redis, reset_redis):
        """reset_redis can be used for removing records multiple times."""
        redis.set("AAA-1", 1)
        redis.set("AAA-2", 2)
        redis.set("BBB-3", 3)

        reset_redis("AAA-*")
        assert not redis.get("AAA-1")
        assert not redis.get("AAA-2")

        assert redis.get("BBB-3")

        reset_redis()
        assert not redis.get("BBB-3")
