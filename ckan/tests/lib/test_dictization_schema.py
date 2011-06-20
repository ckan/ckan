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

from ckan.logic.schema import default_package_schema, default_group_schema

from ckan.lib.navl.dictization_functions import validate

class TestBasicDictize:
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

        context = {'model': model,
                   'session': model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        package_id = pkg.id

        result = package_dictize(pkg, context)

        self.remove_changable_columns(result)

        pprint(result)

        result['name'] = 'anna2'

        converted_data, errors = validate(result, default_package_schema(), context)


        pprint(errors)
        assert converted_data == {'extras': [{'key': u'genre', 'value': u'"romantic novel"'},
                                            {'key': u'original media', 'value': u'"book"'}],
#                                 'groups': [{'name': u'david'}, {'name': u'roger'}],
                                 'license_id': u'other-open',
                                 'name': u'anna2',
                                 'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
                                 'resources': [{'alt_url': u'alt123',
                                                'description': u'Full text. Needs escaping: " Umlaut: \xfc',
                                                'format': u'plain text',
                                                'hash': u'abc123',
                                                'size': u'123',
                                                'url': u'http://www.annakarenina.com/download/x=1&y=2'},
                                               {'alt_url': u'alt345',
                                                'description': u'Index of the novel',
                                                'format': u'json',
                                                'hash': u'def456',
                                                'size': u'345',
                                                'url': u'http://www.annakarenina.com/index.json'}],
                                 'tags': [{'name': u'russian'}, {'name': u'tolstoy'}],
                                 'title': u'A Novel By Tolstoy',
                                 'url': u'http://www.annakarenina.com',
                                 'version': u'0.7a'}, pformat(converted_data)



        assert not errors, errors

        data = converted_data
        data['name'] = u'annakarenina'
        data.pop("title")
        data["resources"][0]["url"] = 'fsdfafasfsaf'
        data["resources"][1].pop("url") 

        converted_data, errors = validate(data, default_package_schema(), context)

        assert errors == {
            'name': [u'Package name already exists in database'],
            'resources': [{},
                          {'url': [u'Missing value']}]
        }, pformat(errors)

        data["id"] = package_id

        converted_data, errors = validate(data, default_package_schema(), context)

        assert errors == {
            'resources': [{}, {'url': [u'Missing value']}]
        }, pformat(errors)

        data['name'] = '????jfaiofjioafjij'
        converted_data, errors = validate(data, default_package_schema(), context)
        assert errors == {
            'name': [u'Name must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'],
            'resources': [{}, {'url': [u'Missing value']}]
        },pformat(errors)

    def test_2_group_schema(self):

        context = {'model': model,
                   'session': model.Session}

        group = model.Session.query(model.Group).first()

        data = group_dictize(group, context)

        converted_data, errors = validate(data, default_group_schema(), context)
        group_pack = sorted(group.packages, key=lambda x:x.id)

        converted_data["packages"] = sorted(converted_data["packages"], key=lambda x:x["id"])

        expected = {'description': u'These are books that David likes.',
                                 'id': group.id,
                                 'name': u'david',
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

        converted_data, errors = validate(data, default_group_schema(), context)
        assert errors ==  {'packages': [{'id': [u'Package was not found.']}, {'id': [u'Missing value']}]} , pformat(errors)

