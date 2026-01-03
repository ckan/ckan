from __future__ import annotations

from ckan.common import CKANConfig
from ckan.config.declaration import Key, Declaration
from ckan.config.declaration.load import loader


class TestFilesLoader:
    def test_no_file_declarations_by_default(self):
        """If storages are not configred, new declarations do not appear."""
        decl = Declaration()
        loader(decl, "files", config=CKANConfig())
        assert not decl

    def test_unknown_storage_type(self):
        """Unknown adapter type registers only declaration of type itself."""
        decl = Declaration()
        opt = "ckan.files.storage.test.type"
        loader(decl, "files", config=CKANConfig({opt: "hehe"}))

        assert list(decl.iter_options()) == [opt]

    def test_missing_storage_type(self):
        """Unknown options only add declaration of the adapter type for the storage."""
        decl = Declaration()
        prefix = "ckan.files.storage.test"
        loader(decl, "files", config=CKANConfig({f"{prefix}.name": "test"}))

        assert list(decl.iter_options()) == [f"{prefix}.type"]

    def test_multiple_missing_storage_type(self):
        """Every unique storage name produces its own declarations."""
        decl = Declaration()
        prefix = "ckan.files.storage"
        loader(
            decl,
            "files",
            config=CKANConfig({f"{prefix}.test.name": "test", f"{prefix}.42.name": "42"}),
        )

        assert sorted(decl.iter_options()) == sorted(
            [f"{prefix}.test.type", f"{prefix}.42.type"]
        )

    def test_fs_storage_type(self):
        """Using a real adapter as a type produces more declarations"""
        decl = Declaration()
        prefix = Key.from_string("ckan.files.storage.test")
        loader(decl, "files", config=CKANConfig({f"{prefix}.type": "ckan:fs"}))

        expected = sorted(
            [
                prefix.type,
                prefix.max_size,
                prefix.supported_types,
                prefix.override_existing,
                prefix.name,
                prefix.location_transformers,
                prefix.path,
                prefix.initialize,
                prefix.disabled_capabilities,
            ]
        )

        actual = sorted(decl.iter_options())

        assert actual == expected
