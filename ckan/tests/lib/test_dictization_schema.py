from nose.tools import assert_equal
from pprint import pprint, pformat
from difflib import unified_diff

from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization import (table_dictize,
                                  table_dict_save)

from ckan.lib.dictization.model_dictize import (package_dictize,
                                                group_dictize
                                               )

from ckan.lib.dictization.model_save import package_dict_save

from ckan.logic.schema import default_package_schema, default_group_schema, \
    default_tags_schema

from ckan.lib.navl.dictization_functions import validate

class TestBasicDictize:

    def setup(self):
        self.context = {'model': model,
                        'session': model.Session}

    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        model.Session.remove()

    def remove_changable_columns(self, dict):
        for key, value in dict.items():
            if key.endswith('id') and key <> 'license_id':
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict)
        return dict

    def remove_revision_id(self, dict):
        for key, value in dict.items():
            if key == 'revision_id':
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_revision_id(new_dict)
        return dict

    def test_1_package_schema(self):

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        package_id = pkg.id

        result = package_dictize(pkg, self.context)

        self.remove_changable_columns(result)

        pprint(result)

        result['name'] = 'anna2'

        converted_data, errors = validate(result, default_package_schema(), self.context)


        pprint(errors)
        assert converted_data == {'extras': [{'key': u'genre', 'value': u'"romantic novel"'},
                                            {'key': u'original media', 'value': u'"book"'}],
                                 'groups': [{'name': u'david'}, {'name': u'roger'}],
                                 'license_id': u'other-open',
                                 'name': u'anna2',
                                 'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
                                 'resources': [{'alt_url': u'alt123',
                                                'description': u'Full text. Needs escaping: " Umlaut: \xfc',
                                                'format': u'plain text',
                                                'hash': u'abc123',
                                                'size_extra': u'123',
                                                'url': u'http://www.annakarenina.com/download/x=1&y=2'},
                                               {'alt_url': u'alt345',
                                                'description': u'Index of the novel',
                                                'format': u'json',
                                                'hash': u'def456',
                                                'size_extra': u'345',
                                                'url': u'http://www.annakarenina.com/index.json'}],
                                 'tags': [{'name': u'Flexible \u30a1'},
                                          {'name': u'russian'},
                                          {'name': u'tolstoy'}],
                                 'title': u'A Novel By Tolstoy',
                                 'url': u'http://www.annakarenina.com',
                                 'version': u'0.7a'}, pformat(converted_data)



        assert not errors, errors

        data = converted_data
        data['name'] = u'annakarenina'
        data.pop("title")
        data["resources"][0]["url"] = 'fsdfafasfsaf'
        data["resources"][1].pop("url") 

        converted_data, errors = validate(data, default_package_schema(), self.context)

        assert errors == {
            'name': [u'That URL is already in use.'],
            #'resources': [{}
            #              {'name': [u'That URL is already in use.']}]
        }, pformat(errors)

        data["id"] = package_id

        converted_data, errors = validate(data, default_package_schema(), self.context)

        assert errors == {
            #'resources': [{}, {'url': [u'Missing value']}]
        }, pformat(errors)

        data['name'] = '????jfaiofjioafjij'
        converted_data, errors = validate(data, default_package_schema(), self.context)
        assert errors == {
            'name': [u'Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'],
            #'resources': [{}, {'url': [u'Missing value']}]
        },pformat(errors)

    def test_2_group_schema(self):

        group = model.Session.query(model.Group).first()

        data = group_dictize(group, self.context)

        converted_data, errors = validate(data, default_group_schema(), self.context)
        group_pack = sorted(group.active_packages().all(), key=lambda x:x.id)

        converted_data["packages"] = sorted(converted_data["packages"], key=lambda x:x["id"])

        expected = {'description': u'These are books that David likes.',
                                 'id': group.id,
                                 'name': u'david',
                                 'type': u'group',
                                 'packages': sorted([{'id': group_pack[0].id},
                                              {'id': group_pack[1].id,
                                               }], key=lambda x:x["id"]),
                                 'title': u"Dave's books"}


        assert not errors
        assert converted_data == expected, pformat(converted_data) + '\n\n' + pformat(expected)



        data["packages"].sort(key=lambda x:x["id"])
        data["packages"][0]["id"] = 'fjdlksajfalsf'
        data["packages"][1].pop("id")
        data["packages"][1].pop("name")

        converted_data, errors = validate(data, default_group_schema(), self.context)
        assert errors ==  {'packages': [{'id': [u'Not found: Dataset']}, {'id': [u'Missing value']}]} , pformat(errors)

    def test_3_tag_schema_allows_spaces(self):
        """Asserts that a tag name with space is valid"""
        ignored = ""
        data = {
            'name': u'with space',
            'revision_timestamp': ignored, 
            'state': ignored
            }

        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_4_tag_schema_allows_limited_punctuation(self):
        """Asserts that a tag name with limited punctuation is valid"""
        ignored = ""
        data = {
            'name': u'.-_',
            'revision_timestamp': ignored,
            'state': ignored
            }

        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_5_tag_schema_allows_capital_letters(self):
        """Asserts that tag names can have capital letters"""
        ignored = ""
        data = {
            'name': u'CAPITALS',
            'revision_timestamp': ignored,
            'state': ignored
            }

        _, errors = validate(data, default_tags_schema(), self.context)
        assert not errors, str(errors)

    def test_6_tag_schema_disallows_most_punctuation(self):
        """Asserts most punctuation is disallowed"""
        not_allowed=r'!?"\'+=:;@#~[]{}()*&^%$,'
        ignored = ""
        data = {
            'revision_timestamp': ignored,
            'state': ignored
        }
        for ch in not_allowed:
            data['name'] = "Character " + ch
            _, errors = validate(data, default_tags_schema(), self.context)
            assert errors, pprint(errors)
            assert 'name' in errors
            error_message = errors['name'][0]
            assert data['name'] in error_message, error_message
            assert "must be alphanumeric" in error_message

    def test_7_tag_schema_disallows_whitespace_other_than_spaces(self):
        """Asserts whitespace characters, such as tabs, are not allowed."""
        not_allowed = '\t\n\r\f\v'
        ignored = ""
        data = {
            'revision_timestamp': ignored,
            'state': ignored
        }
        for ch in not_allowed:
            data['name'] = "Bad " + ch + " character"
            _, errors = validate(data, default_tags_schema(), self.context)
            assert errors, repr(ch)
            assert 'name' in errors
            error_message = errors['name'][0]
            assert data['name'] in error_message, error_message
            assert "must be alphanumeric" in error_message
