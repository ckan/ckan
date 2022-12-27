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

    def test_setup(self, ckan_config):
        decl = Declaration()
        decl.setup()

        # setup seals declaration
        with pytest.raises(TypeError):
            decl.annotate("hello")

        # core declarations loaded
        assert Key().ckan.site_url in decl

        # no safe-mode by default
        missing = set(decl.iter_options()) - set(ckan_config)
        assert Key().api_token.jwt.algorithm in missing

        # no normalization by default
        assert isinstance(ckan_config["debug"], str)

    @pytest.mark.ckan_config("config.mode", "strict")
    def test_safe_setup(self, ckan_config):
        delimiter = Key().ckan.template_title_delimiter
        decl = Declaration()

        assert delimiter not in ckan_config
        decl.setup()
        decl.make_safe(ckan_config)
        assert delimiter in ckan_config

    @pytest.mark.ckan_config("config.mode", "strict")
    @pytest.mark.ckan_config("ckan.jobs.timeout", "zero")
    def test_strict_setup(self, ckan_config):
        decl = Declaration()
        decl.setup()
        _, errors = decl.validate(ckan_config)
        assert "ckan.jobs.timeout" in errors

    @pytest.mark.ckan_config("config.mode", "strict")
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

    def test_make_safe_no_effect(self):
        decl = Declaration()
        decl.declare(Key().a, 10)

        cfg = CKANConfig()
        assert not decl.make_safe(cfg)
        assert cfg == CKANConfig()

    def test_make_safe_in_safe_mode(self):
        decl = Declaration()
        decl.declare(Key().a, 10)

        cfg = CKANConfig({"config.mode": "strict"})
        assert decl.make_safe(cfg)
        assert cfg == CKANConfig({"config.mode": "strict", "a": 10})

    def test_make_safe_no_overrides(self):
        decl = Declaration()
        decl.declare(Key().a, 10)

        cfg = CKANConfig({"config.mode": "strict", "a": 20})
        assert decl.make_safe(cfg)
        assert cfg == CKANConfig({"config.mode": "strict", "a": 20})

    def test_normalize_no_effect(self):
        decl = Declaration()
        decl.declare_int(Key().a, "10")

        cfg = CKANConfig()
        assert not decl.normalize(cfg)
        assert cfg == CKANConfig()

    def test_normalize_in_normalized_mode(self):
        decl = Declaration()
        decl.declare_int(Key().a, "10")

        cfg = CKANConfig({"config.mode": "strict"})
        assert decl.normalize(cfg)
        # in non-safe mode default value has no effect
        assert cfg == CKANConfig({"config.mode": "strict"})

        cfg = CKANConfig({"config.mode": "strict", "a": "10"})
        assert decl.normalize(cfg)
        assert cfg == CKANConfig({"config.mode": "strict", "a": 10})
