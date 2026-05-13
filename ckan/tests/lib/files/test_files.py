from __future__ import annotations
import os
from ckan import types
from ckan.lib import files
import pytest


class TestCollectStorages:
    def test_derived_storages_from_default(
        self, ckan_config: types.CKANConfig, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that entity specific storages are collected from the default
        storage, and that they are not collected if the default storage is
        missing.
        """
        default = ckan_config["ckan.files.default_storages.default"]
        resource = ckan_config["ckan.files.default_storages.resource"]
        user = ckan_config["ckan.files.default_storages.user"]
        group = ckan_config["ckan.files.default_storages.group"]
        admin = ckan_config["ckan.files.default_storages.admin"]

        storages = files.collect_storages()
        assert default in storages
        assert resource in storages
        assert user in storages
        assert group in storages
        assert admin in storages

        monkeypatch.setitem(
            ckan_config,
            "ckan.files.default_storages.default",
            "definitely-not-a-default-storage",
        )

        storages = files.collect_storages()

        # this storage is no longer default, but it's still initialized,
        # because it has explicit configuration
        assert default in storages

        # these storages are no longer initialized, because default storage
        # does not exist and they cannot fallback to it
        assert resource not in storages
        assert user not in storages
        assert group not in storages
        assert admin not in storages

    def test_derived_storages_path(self, ckan_config: types.CKANConfig):
        """Test that entity specific storages have the correct path derived
        from the default storage path.

        """
        storages = files.collect_storages()

        default = storages[ckan_config["ckan.files.default_storages.default"]]
        path = default.settings.path
        resource = storages[ckan_config["ckan.files.default_storages.resource"]]
        assert resource.settings.path == os.path.join(path, "resources")

        user = storages[ckan_config["ckan.files.default_storages.user"]]
        assert user.settings.path == os.path.join(path, "storage", "uploads", "user")

        group = storages[ckan_config["ckan.files.default_storages.group"]]
        assert group.settings.path == os.path.join(path, "storage", "uploads", "group")

        admin = storages[ckan_config["ckan.files.default_storages.admin"]]
        assert admin.settings.path == os.path.join(path, "storage", "uploads", "admin")

    def test_derived_storages_have_correct_name(self, ckan_config: types.CKANConfig):
        """Test that entity specific storages have the correct name, even if
        they are derived from the default storage and do not have explicit
        configuration.
        """
        storages = files.collect_storages()

        for type in ["default", "resource", "user", "group", "admin"]:
            name = ckan_config[f"ckan.files.default_storages.{type}"]
            storage = storages[name]
            assert (
                storage.settings.name
                == ckan_config[f"ckan.files.default_storages.{type}"]
            )

    def test_derived_storages_have_correct_public_setting(
        self, ckan_config: types.CKANConfig
    ):
        """Test that entity specific storages have the correct value of the
        public flag.

        """
        storages = files.collect_storages()

        for type in ["default", "resource"]:
            name = ckan_config[f"ckan.files.default_storages.{type}"]
            storage = storages[name]
            assert not storage.settings.public  # pyright: ignore[reportAttributeAccessIssue]

        for type in ["user", "group", "admin"]:
            name = ckan_config[f"ckan.files.default_storages.{type}"]
            storage = storages[name]
            assert storage.settings.public  # pyright: ignore[reportAttributeAccessIssue]
