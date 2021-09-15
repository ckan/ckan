import pytest
from ckan.config import Key
from ckan.config.utils import Option, Pattern


class TestKey:
    def test_constructors(self):
        staged = Key().ckan.site_url
        listed = Key(["ckan", "site_url"])
        parsed = Key.from_string("ckan.site_url")

        assert staged == listed
        assert staged == parsed

    @pytest.mark.parametrize(
        "string",
        [
            "ckan",
            "ckan.site_url",
            "ckan.auth.create_unowned_datasets",
            "a.b.c.d.e.f",
        ],
    )
    def test_string_equality(self, string):
        assert Key.from_string(string) == string

    def test_curry(self):
        ckan = Key().ckan
        assert ckan == "ckan"

        auth = ckan.auth
        assert auth == "ckan.auth"

        unowned = auth.create_unowned_datasets
        assert unowned == "ckan.auth.create_unowned_datasets"

        assert unowned == Key().ckan.auth.create_unowned_datasets

    def test_config_access(self, ckan_config):
        assert ckan_config["ckan.site_url"] is ckan_config[Key().ckan.site_url]

    def test_hash(self):
        option = Key().a.b.c
        assert {option: ""} == {"a.b.c": ""}

    @pytest.mark.parametrize(
        "name,length",
        [
            ("", 0),
            ("ckan", 1),
            ("ckan.auth", 2),
            ("x.y.z", 3),
            ("......", 0),
            (".a..b.", 2),
        ],
    )
    def test_length(self, name, length):
        assert len(Key.from_string(name)) == length

    def test_index_access(self):
        option = Key().a.b.c.d.e.f

        assert option[0] == "a"
        assert option[-1] == "f"
        assert option[1:4] == Key().b.c.d

    @pytest.mark.parametrize(
        "left, right, expected",
        [
            (Key(), Key(), Key()),
            ("", Key(), Key()),
            (Key(), "", Key()),
            (Key().a, Key().b, Key().a.b),
            (Key().a, "b", Key().a.b),
            ("a", Key().b, Key().a.b),
            (Key().a.b.c, Key().x.y.z, Key().a.b.c.x.y.z),
            (Key().a.b.c, "x.y.z", Key().a.b.c.x.y.z),
            ("a.b.c", Key().x.y.z, Key().a.b.c.x.y.z),
        ],
    )
    def test_addition(self, left, right, expected):
        assert left + right == expected


class TestDetails:
    def test_default_value(self):
        assert Option("def").has_default()
        assert Option("").has_default()
        assert Option(None).has_default()
        assert Option(False).has_default()

        assert not Option().has_default()


class TestPattern:
    @pytest.mark.parametrize(
        "pattern, key",
        [
            ("a.b.c", "a.b.c"),
            ("*.b.c", "a.b.c"),
            ("a.*.c", "a.b.c"),
            ("a.b.*", "a.b.c"),
            ("*.b.*", "a.b.c"),
            ("*.*.c", "a.b.c"),
            ("a.*.*", "a.b.c"),
            ("*.*.*", "a.b.c"),
            ("a.b.c.d.e", "a.b.c.d.e"),
            ("a.b.c.*.e", "a.b.c.d.e"),
            ("a.*.c.*.e", "a.b.c.d.e"),
            ("a.*.e", "a.b.c.d.e"),
            ("a.*.c.*.f", "a.b.c.d.e.f"),
            ("a.*.c.*.*", "a.b.c.d.e.f"),
            ("a.*.*.*.*", "a.b.c.d.e.f"),
            ("a.*", "a.b.c.d.e.f"),
            ("*", "a.b.c.d.e"),
        ],
    )
    def test_match(self, pattern, key):
        assert Pattern.from_string(pattern) == Key.from_string(key)

    @pytest.mark.parametrize(
        "pattern, key",
        [
            ("b.*.*", "a.b.c"),
            ("*.a.*", "a.b.c"),
            ("*.a.*.*", "a.b.c"),
            ("a.*.b.c.d.e", "a.b.c.d.e"),
            ("*.a.b.c.d.e", "a.b.c.d.e"),
            ("a.b.c.d.e.*", "a.b.c.d.e"),
            ("*.a.b.*.c.d.e.*", "a.b.c.d.e"),
            ("a.*.*.*.*", "a.b"),
            ("a.*.x", "a.b.c"),
            ("*.c.b", "a.b.c"),
        ],
    )
    def test_does_non_match(self, pattern, key):
        assert Pattern.from_string(pattern) != Key.from_string(key)
