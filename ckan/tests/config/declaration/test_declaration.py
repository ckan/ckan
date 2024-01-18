# -*- coding: utf-8 -*-

from ckan.common import CKANConfig
from ckan.config.declaration.load import GroupV1, OptionV1
import pytest

from ckan.config.declaration import Declaration, Key, Pattern, Flag


class TestDeclaration:
    def test_base_declaration_is_falsy(self):
        decl = Declaration()
        assert not decl

    def test_annotations_make_declaration_non_empty(self):
        decl = Declaration()
        decl.annotate("Hello")
        assert decl

    def test_option_make_declaration_non_empty(self):
        decl = Declaration()
        decl.declare(Key().test)
        assert decl

    def test_declarations_are_gettable(self):
        decl = Declaration()
        key = Key().test
        decl.declare(key, 1)

        option = decl[key]
        assert option.default == 1

    def test_basic_iteration(self):
        key = Key()
        decl = Declaration()
        decl.annotate("Start")

        decl.declare(key.a)
        decl.declare(key.b)

        assert list(decl.iter_options()) == [key.a, key.b]

    def test_pattern_and_flag_iteration(self):
        key = Key()
        decl = Declaration()
        decl.annotate("Start")

        decl.declare(key.aloha)
        decl.declare(key.hello)
        decl.declare(key.hey).set_flag(Flag.ignored)

        pattern = key.dynamic("anything")
        assert list(decl.iter_options(pattern=pattern)) == [
            key.aloha,
            key.hello,
        ]

        pattern = Pattern(key) + "he*"
        assert list(decl.iter_options(pattern=pattern)) == [key.hello]

        assert list(decl.iter_options(exclude=Flag(0))) == [
            key.aloha,
            key.hello,
            key.hey,
        ]

    def test_required_option(self):
        decl = Declaration()
        key = "test.required.flag.adds.not_empty"
        option = decl.declare(key)
        _, errors = decl.validate({})
        assert not errors

        option.set_flag(Flag.required)
        _, errors = decl.validate({})
        assert key in errors

    def test_setup(self, ckan_config):
        decl = Declaration()
        decl.setup()

        # setup seals declaration
        with pytest.raises(TypeError):
            decl.annotate("hello")

        # core declarations loaded
        assert Key().ckan.site_url in decl

        # normalization changed types
        assert isinstance(ckan_config["debug"], bool)

    @pytest.mark.ckan_config("ckan.jobs.timeout", "zero")
    def test_strict_setup(self, ckan_config):
        decl = Declaration()
        decl.setup()
        _, errors = decl.validate(ckan_config)
        assert "ckan.jobs.timeout" in errors

    def test_normalized_setup(self, ckan_config):
        decl = Declaration()
        decl.setup()
        decl.normalize(ckan_config)
        assert ckan_config["testing"] is True

    def test_load_core(self):
        k = Key().ckan.site_url
        decl = Declaration()
        assert k not in decl

        decl.load_core_declaration()
        assert k in decl

    def test_load_plugin(self):
        k = Key().ckan.datastore.write_url
        decl = Declaration()
        assert k not in decl

        decl.load_plugin("datapusher")
        assert k not in decl

        decl.load_plugin("datastore")
        assert k in decl

    def test_load_dict(self):
        k = Key().hello.world
        decl = Declaration()
        assert k not in decl

        option: OptionV1 = {"key": str(k)}

        group: GroupV1 = {
            "annotation": "hello",
            "options": [option],
        }

        decl.load_dict({"version": 1, "groups": [group]})

        assert k in decl

    def test_make_safe_uses_defaults(self):
        decl = Declaration()
        decl.declare(Key().a, 10)

        cfg = CKANConfig()
        decl.make_safe(cfg)
        assert cfg == CKANConfig({"a": 10})

    def test_make_safe_no_overrides(self):
        decl = Declaration()
        decl.declare(Key().a, 10)

        cfg = CKANConfig({"a": 20})
        decl.make_safe(cfg)
        assert cfg == CKANConfig({"a": 20})

    def test_normalize_convert_types(self):
        decl = Declaration()
        decl.declare_int(Key().a, "10")

        cfg = CKANConfig()
        decl.normalize(cfg)
        # in non-safe mode default value has no effect
        assert cfg == CKANConfig()

        decl.make_safe(cfg)
        decl.normalize(cfg)
        assert cfg == CKANConfig({"a": 10})

        cfg = CKANConfig({"a": "20"})
        decl.normalize(cfg)
        assert cfg == CKANConfig({"a": 20})

    @pytest.mark.parametrize("raw,safe", [
        ({}, {"a": "default"}),
        ({"legacy_a": "legacy"}, {"a": "legacy", "legacy_a": "legacy"}),
        ({"a": "modern", "legacy_a": "legacy"}, {"a": "modern", "legacy_a": "legacy"}),
    ])
    def test_legacy_key(self, raw, safe):
        decl = Declaration()
        option = decl.declare(Key().a, "default")
        option.legacy_key = "legacy_a"

        cfg = CKANConfig(raw)
        decl.make_safe(cfg)
        assert cfg == CKANConfig(safe)
