# encoding: utf-8

from pprint import pformat
import pytest
from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization.model_dictize import package_dictize, group_dictize
from ckan.logic.schema import (
    default_create_package_schema,
    default_update_package_schema,
    default_group_schema,
    default_tags_schema,
)
from ckan.lib.navl.dictization_functions import validate


class TestBasicDictize(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        CreateTestData.create()
        self.context = {"model": model, "session": model.Session}

    def remove_changable_columns(self, dict):
        for key, value in list(dict.items()):
            if key.endswith("id") and key != "license_id":
                dict.pop(key)
            if key in ("created", "metadata_modified"):
                dict.pop(key)

            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict)
        return dict

    def test_1_package_schema(self):
        pkg = (
            model.Session.query(model.Package)
            .filter_by(name="annakarenina")
            .first()
        )

        package_id = pkg.id
        result = package_dictize(pkg, self.context)
        self.remove_changable_columns(result)

        result["name"] = "anna2"
        # we need to remove these as they have been added
        del result["relationships_as_object"]
        del result["relationships_as_subject"]

        converted_data, errors = validate(
            result, default_create_package_schema(), self.context
        )

        expected_data = {
            "extras": [
                {"key": "genre", "value": "romantic novel"},
                {"key": "original media", "value": "book"},
            ],
            "groups": [
                {"name": "david", "title": "Dave's books"},
                {"name": "roger", "title": "Roger's books"},
            ],
            "license_id": "other-open",
            "name": "anna2",
            "type": "dataset",
            "notes": "Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n\nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n",
            "private": False,
            "resources": [
                {
                    "alt_url": "alt123",
                    "description": 'Full text. Needs escaping: " Umlaut: \xfc',
                    "format": "plain text",
                    "hash": "abc123",
                    "size_extra": "123",
                    "url": "http://datahub.io/download/x=1&y=2",
                },
                {
                    "alt_url": "alt345",
                    "description": "Index of the novel",
                    "format": "JSON",
                    "hash": "def456",
                    "size_extra": "345",
                    "url": "http://datahub.io/index.json",
                },
            ],
            "tags": [
                {"name": "Flexible \u30a1"},
                {"name": "russian"},
                {"name": "tolstoy"},
            ],
            "title": "A Novel By Tolstoy",
            "url": "http://datahub.io",
            "version": "0.7a",
        }

        assert converted_data == expected_data, pformat(converted_data)
        assert not errors, errors

        data = converted_data
        data["name"] = "annakarenina"
        data.pop("title")
        data["resources"][0]["url"] = "fsdfafasfsaf"
        data["resources"][1].pop("url")

        converted_data, errors = validate(
            data, default_create_package_schema(), self.context
        )

        assert errors == {"name": ["That URL is already in use."]}, pformat(
            errors
        )

        data["id"] = package_id
        data["name"] = "????jfaiofjioafjij"

        converted_data, errors = validate(
            data, default_update_package_schema(), self.context
        )
        assert errors == {
            "name": [
                "Must be purely lowercase alphanumeric (ascii) "
                "characters and these symbols: -_"
            ]
        }, pformat(errors)

    def test_2_group_schema(self):
        group = model.Session.query(model.Group).first()
        data = group_dictize(group, self.context)

        # we don't want these here
        del data["groups"]
        del data["users"]
        del data["tags"]
        del data["extras"]

        converted_data, errors = validate(
            data, default_group_schema(), self.context
        )
        group_pack = sorted(group.packages(), key=lambda x: x.id)

        converted_data["packages"] = sorted(
            converted_data["packages"], key=lambda x: x["id"]
        )

        expected = {
            "description": "These are books that David likes.",
            "id": group.id,
            "name": "david",
            "is_organization": False,
            "type": "group",
            "image_url": "",
            "image_display_url": "",
            "packages": sorted(
                [
                    {
                        "id": group_pack[0].id,
                        "name": group_pack[0].name,
                        "title": group_pack[0].title,
                    },
                    {
                        "id": group_pack[1].id,
                        "name": group_pack[1].name,
                        "title": group_pack[1].title,
                    },
                ],
                key=lambda x: x["id"],
            ),
            "title": "Dave's books",
            "approval_status": "approved",
        }

        assert not errors
        assert converted_data == expected, pformat(converted_data)

        data["packages"].sort(key=lambda x: x["id"])
        data["packages"][0]["id"] = "fjdlksajfalsf"
        data["packages"][1].pop("id")
        data["packages"][1].pop("name")

        converted_data, errors = validate(
            data, default_group_schema(), self.context
        )
        assert errors == {
            "packages": [
                {"id": ["Not found: Dataset"]},
                {"id": ["Missing value"]},
            ]
        }, pformat(errors)

    def test_3_tag_schema_allows_spaces(self):
        """Asserts that a tag name with space is valid"""
        ignored = ""
        data = {
            "name": "with space",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_4_tag_schema_allows_limited_punctuation(self):
        """Asserts that a tag name with limited punctuation is valid"""
        ignored = ""
        data = {
            "name": ".-_",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_5_tag_schema_allows_capital_letters(self):
        """Asserts that tag names can have capital letters"""
        ignored = ""
        data = {
            "name": "CAPITALS",
            "revision_timestamp": ignored,
            "state": ignored,
        }
        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_6_tag_schema_disallows_most_punctuation(self):
        """Asserts most punctuation is disallowed"""
        not_allowed = r'!?"\'+=:;@#~[]{}()*&^%$,'
        ignored = ""
        data = {"revision_timestamp": ignored, "state": ignored}
        for ch in not_allowed:
            data["name"] = "Character " + ch
            _, errors = validate(data, default_tags_schema(), self.context)
            assert errors
            assert "name" in errors
            error_message = errors["name"][0]
            assert data["name"] in error_message, error_message
            assert "can only contain alphanumeric characters" in error_message

    def test_7_tag_schema_disallows_whitespace_other_than_spaces(self):
        """Asserts whitespace characters, such as tabs, are not allowed."""
        not_allowed = "\t\n\r\f\v"
        ignored = ""
        data = {"revision_timestamp": ignored, "state": ignored}
        for ch in not_allowed:
            data["name"] = "Bad " + ch + " character"
            _, errors = validate(data, default_tags_schema(), self.context)
            assert errors, repr(ch)
            assert "name" in errors
            error_message = errors["name"][0]
            assert data["name"] in error_message, error_message
            assert "can only contain alphanumeric characters" in error_message
