from ckan.config.declaration.load import GroupV1, OptionV1
from ckan.exceptions import CkanConfigurationException
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
        decl.declare(key.hey).ignore()

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
        decl.setup(ckan_config)

        # setup seals declaration
        with pytest.raises(TypeError):
            decl.annotate("hello")

        # core declarations loaded
        assert Key().ckan.site_url in decl

        # no safe-mode by default
        missing = set(decl.iter_options()) - set(ckan_config)
        assert Key().config.safe in missing

        # no normalization by default
        assert isinstance(ckan_config["debug"], str)

    @pytest.mark.ckan_config("config.safe", "true")
    def test_safe_setup(self, ckan_config):
        strict = Key().config.strict
        decl = Declaration()

        assert strict not in ckan_config
        decl.setup(ckan_config)
        assert strict in ckan_config

    @pytest.mark.ckan_config("config.strict", "true")
    @pytest.mark.ckan_config("ckan.jobs.timeout", "zero")
    def test_strict_setup(self, ckan_config):
        decl = Declaration()
        with pytest.raises(
            CkanConfigurationException,
            match="ckan.jobs.timeout: Please enter an integer value",
        ):
            decl.setup(ckan_config)

    @pytest.mark.ckan_config("config.normalized", "true")
    @pytest.mark.ckan_config("ckan.jobs.timeout", "zero")
    def test_normalized_setup(self, ckan_config):
        decl = Declaration()
        decl.setup(ckan_config)
        assert ckan_config["config.normalized"] is True
        assert ckan_config["ckan.jobs.timeout"] == "zero"

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

        option: OptionV1 = {
            "key": str(k)
        }

        group: GroupV1 = {
            "annotation": "hello",
            "options": [option],
        }

        decl.load_dict({
            "version": 1,
            "groups": [group]
        })

        assert k in decl
