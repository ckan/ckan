# encoding: utf-8

import unittest.mock as mock
import json
import pytest
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import xml.etree.ElementTree as ET


class TestDatastoreDump(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_basic(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"book": "annakarenina"}, {u"book": "warandpeace"}],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f'/datastore/dump/{resource["id"]}')
        assert (
            "_id,book\r\n"
            "1,annakarenina\n"
            "2,warandpeace\n" == response.get_data(as_text=True)
        )

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_all_fields_types(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f'/datastore/dump/{resource["id"]}')
        content = response.get_data(as_text=True)
        expected = (
            "_id,b\xfck,author,published" ",characters,random_letters,nested"
        )
        assert content[: len(expected)] == expected
        assert "warandpeace" in content
        assert '"[""Princess Anna"",""Sergius""]"' in content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_alias(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "aliases": "books",
            "records": [{u"book": "annakarenina"}, {u"book": "warandpeace"}],
        }
        helpers.call_action("datastore_create", **data)

        # get with alias instead of id
        response = app.get("/datastore/dump/books")
        assert (
            "_id,book\r\n"
            "1,annakarenina\n"
            "2,warandpeace\n" == response.get_data(as_text=True)
        )

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_does_not_exist_raises_404(self, app):

        app.get("/datastore/dump/does-not-exist", status=404)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_limit(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"book": "annakarenina"}, {u"book": "warandpeace"}],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(
            "/datastore/dump/{0}?limit=1".format(str(resource["id"]))
        )
        expected_content = "_id,book\r\n" "1,annakarenina\n"
        assert response.get_data(as_text=True) == expected_content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_q_and_fields(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(
            u"/datastore/dump/{0}?q=warandpeace&fields=nested,author".format(
                resource["id"]
            )
        )
        expected_content = "nested,author\r\n" '"{""a"": ""b""}",tolstoy\n'
        assert response.get_data(as_text=True) == expected_content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_csv_file_extension(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(
            u"/datastore/dump/{0}?limit=1&format=csv".format(
                resource["id"]
            )
        )

        attachment_filename = res.headers['Content-disposition']

        expected_attch_filename = 'attachment; filename="{0}.csv"'.format(
            resource['id'])

        assert attachment_filename == expected_attch_filename

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_tsv(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(
            "/datastore/dump/{0}?limit=1&format=tsv".format(
                str(resource["id"])
            )
        )

        expected_content = (
            "_id\tb\xfck\tauthor\tpublished\tcharacters\trandom_letters\t"
            "nested\r\n1\tannakarenina\ttolstoy\t2005-03-01T00:00:00\t"
            '"[""Princess Anna"",""Sergius""]"\t'
            '"[""a"",""e"",""x""]"\t"[""b"", '
            '{""moo"": ""moo""}]"\n'
        )
        assert res.get_data(as_text=True) == expected_content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_tsv_file_extension(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(f"/datastore/dump/{resource['id']}?limit=1&format=tsv")

        attachment_filename = res.headers['Content-disposition']

        expected_attch_filename = 'attachment; filename="{0}.tsv"'.format(
            resource['id'])

        assert attachment_filename == expected_attch_filename

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_json(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(
            "/datastore/dump/{0}?limit=1&format=json".format(
                resource["id"]
            )
        )

        content = json.loads(res.data)
        expected_content = {
            u'fields': [
                {u'id': u'_id', u'type': u'int'},
                {u'id': u'bük', u'type': u'text'},
                {u'id': u'author', u'type': u'text'},
                {u'id': u'published', u'type': u'timestamp'},
                {u'id': u'characters', u'type': u'_text'},
                {u'id': u'random_letters', u'type': u'_text'},
                {u'id': u'nested', u'type': u'json'}
            ],
            u'records': [
                [
                    1, u'annakarenina', u'tolstoy', u'2005-03-01T00:00:00',
                    [u'Princess Anna', u'Sergius'],
                    [u'a', u'e', u'x'],
                    [u'b', {u'moo': u'moo'}]
                ]
            ]
        }
        assert content == expected_content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_json_file_extension(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(f"/datastore/dump/{resource['id']}?limit=1&format=json")

        attachment_filename = res.headers['Content-disposition']

        expected_attch_filename = 'attachment; filename="{0}.json"'.format(
            resource['id'])

        assert attachment_filename == expected_attch_filename

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_xml(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(f"/datastore/dump/{resource['id']}?limit=1&format=xml")
        expected_content = (
            u'<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            r'<row _id="1">'
            u"<b\xfck>annakarenina</b\xfck>"
            u"<author>tolstoy</author>"
            u"<published>2005-03-01T00:00:00</published>"
            u"<characters>"
            u'<value key="0">Princess Anna</value>'
            u'<value key="1">Sergius</value>'
            u"</characters>"
            u"<random_letters>"
            u'<value key="0">a</value>'
            u'<value key="1">e</value>'
            u'<value key="2">x</value>'
            u"</random_letters>"
            u"<nested>"
            u'<value key="0">b</value>'
            u'<value key="1">'
            u'<value key="moo">moo</value>'
            u"</value>"
            u"</nested>"
            u"</row>\n"
            u"</data>\n"
        )
        assert res.get_data(as_text=True) == expected_content

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_xml_file_extension(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "random_letters", "type": "text[]"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "random_letters": ["a", "e", "x"],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "random_letters": [],
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(f"/datastore/dump/{resource['id']}?limit=1&format=xml")

        attachment_filename = res.headers['Content-disposition']

        expected_attch_filename = 'attachment; filename="{0}.xml"'.format(
            resource['id'])

        assert attachment_filename == expected_attch_filename

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_xml_col_name_conformity(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "fields": [
                {"id": "278bad_name", "type": "text"},
                {"id": "xmlbad_name", "type": "text"},
                {"id": "bad name", "type": "text"},
                {"id": "bad_(name)", "type": "text"},
                {"id": ".bad_name", "type": "text"},
                {"id": "-bad_name", "type": "text"},
            ],
            "records": [
                {
                    "278bad_name": "example",  # cannot start with numbers
                    "xmlbad_name": "example 0",  # cannot start with "xml"
                    "bad name": "example 1",  # cannot have spaces
                    "bad_(name)": "example 2",  # cannot have special chars
                    ".bad_name": "example 3",  # cannot start with period
                    "-bad_name": "example 4",  # cannot start with hyphen
                },
            ],
        }
        helpers.call_action("datastore_create", **data)

        res = app.get(f"/datastore/dump/{resource['id']}?format=xml")
        body = res.get_data(as_text=True)

        # bad names should not exist in the xml content
        assert '278bad_name' not in body
        assert 'xmlbad_name' not in body
        assert 'bad name' not in body
        assert 'bad_(name)' not in body
        assert '.bad_name' not in body
        assert '-bad_name' not in body

        xml = ET.fromstring(body)

        # same keys will be appended with incrementing number
        expected_obj = {
            'bad_name': 'example',
            'bad_name_0': 'example 0',
            'bad_name_1': 'example 1',
            'bad_name_2': 'example 2',
            'bad_name_3': 'example 3',
            'bad_name_4': 'example 4',
        }

        row = xml.find('row')

        for tag, value in expected_obj.items():
            obj = row.find(tag)
            assert obj is not None
            assert obj.text == value

    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "3")
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_dump_with_low_rows_max(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}")
        assert get_csv_record_values(response.data) == list(range(12))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 5)
    def test_dump_pagination(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}")
        assert get_csv_record_values(response.data) == list(range(12))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "7")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 5)
    def test_dump_pagination_with_limit(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=11")
        assert get_csv_record_values(response.data) == list(range(11))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "7")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 6)
    def test_dump_pagination_csv_with_limit_same_as_paginate(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=6")
        assert get_csv_record_values(response.data) == list(range(6))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "6")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 5)
    def test_dump_pagination_with_rows_max(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=7")
        assert get_csv_record_values(response.data) == list(range(7))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "6")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 6)
    def test_dump_pagination_with_rows_max_same_as_paginate(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=7")
        assert get_csv_record_values(response.data) == list(range(7))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "7")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 5)
    def test_dump_pagination_json_with_limit(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=6&format=json")
        assert get_json_record_values(response.data) == list(range(6))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "6")
    @mock.patch("ckanext.datastore.blueprint.PAGINATE_BY", 5)
    def test_dump_pagination_json_with_rows_max(self, app):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{u"record": str(num)} for num in list(range(12))],
        }
        helpers.call_action("datastore_create", **data)

        response = app.get(f"/datastore/dump/{resource['id']}?limit=7&format=json")
        assert get_json_record_values(response.data) == list(range(7))


def get_csv_record_values(response_body):
    records = response_body.decode().split()[1:]
    return [int(record.split(",")[1]) for record in records]


def get_json_record_values(response_body):
    return [record[1] for record in json.loads(response_body)["records"]]
