import pytest
from ckan.config import Option


class TestOption:
    def test_constructors(self):
        staged = Option().ckan.site_url
        listed = Option(["ckan", "site_url"])
        parsed = Option.from_string("ckan.site_url")

        assert staged == listed
        assert staged == parsed

    @pytest.mark.parametrize("string", [
        "ckan", "ckan.site_url", "ckan.auth.create_unowned_datasets",
        "a.b.c.d.e.f"
    ])
    def test_string_equality(self, string):
        assert Option.from_string(string) == string

    def test_curry(self):
        ckan = Option().ckan
        assert ckan == "ckan"

        auth = ckan.auth
        assert auth == "ckan.auth"

        unowned = auth.create_unowned_datasets
        assert unowned == "ckan.auth.create_unowned_datasets"

        assert unowned == Option().ckan.auth.create_unowned_datasets

    def test_config_access(self, ckan_config):
        assert ckan_config["ckan.site_url"] is ckan_config[Option().ckan.site_url]

    def test_hash(self):
        option = Option().a.b.c
        assert {option: ""} == {"a.b.c": ""}

    @pytest.mark.parametrize("name,length", [
        ("", 0),
        ("ckan", 1),
        ("ckan.auth", 2),
        ("x.y.z", 3),
        ("......", 0),
        (".a..b.", 2)
    ])
    def test_length(self, name, length):
        assert len(Option.from_string(name)) == length

    def test_index_access(self):
        option = Option().a.b.c.d.e.f

        assert option[0] == "a"
        assert option[-1] == "f"
        assert option[1:4] == Option().b.c.d

    @pytest.mark.parametrize("left, right, expected", [
        (Option(), Option(), Option()),
        ("", Option(), Option()),
        (Option(), "", Option()),
        (Option().a, Option().b, Option().a.b),
        (Option().a, "b", Option().a.b),
        ("a", Option().b, Option().a.b),
        (Option().a.b.c, Option().x.y.z, Option().a.b.c.x.y.z),
        (Option().a.b.c, "x.y.z", Option().a.b.c.x.y.z),
        ("a.b.c", Option().x.y.z, Option().a.b.c.x.y.z),
    ])
    def test_addition(self, left, right, expected):
        assert left + right == expected
