from __future__ import annotations

from ckan.common import CKANConfig
from ckan.config.declaration import Key, Declaration
from ckan.config.declaration.load import loader, config_tree


class TestConfigTree:
    def test_empty(self):
        result = config_tree(CKANConfig())
        assert result == {}

    def test_noop(self):
        data = {"a.b.c": 1}
        config = CKANConfig(data)
        assert config_tree(config) == data

    def test_prefix_filter(self):
        data = {"a.b.c": 1, "x.y.z": 2, "aaa": 3}
        config = CKANConfig(data)

        assert config_tree(config, prefix="a") == {".b.c": 1, "aa": 3}
        assert config_tree(config, prefix="a.") == {"b.c": 1}
        assert config_tree(config, prefix="x.y.z") == {"": 2}

    def test_depth(self):
        data = {"a.b.c": 1, "x.y.z": 2, "aaa": 3}
        config = CKANConfig(data)

        assert config_tree(config, depth=1) == {
            "a": {"b.c": 1},
            "x": {"y.z": 2},
            "aaa": 3,
        }

        assert config_tree(config, depth=2) == {
            "a": {"b": {"c": 1}},
            "x": {"y": {"z": 2}},
            "aaa": 3,
        }

    def test_keep_prefix(self):
        data = {"a.b.c": 1, "x.y.z": 2, "aaa": 3}
        config = CKANConfig(data)

        assert config_tree(config, prefix="a.", keep_prefix=True) == {"a.b.c": 1}

        assert config_tree(config, prefix="a.", depth=-1) == {"b": {"c": 1}}
        assert config_tree(config, prefix="a.", depth=-1, keep_prefix=True) == {
            "a": {"b": {"c": 1}}
        }


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
