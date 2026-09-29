# encoding: utf-8

import pytest

import ckanext.datastore.backend.postgres as postgres_backend
import ckanext.datastore.helpers as datastore_helpers


class TestTypeGetters(object):
    def test_get_list(self):
        get_list = datastore_helpers.get_list
        assert get_list(None) is None
        assert get_list([]) == []
        assert get_list("") == []
        assert get_list("foo") == ["foo"]
        assert get_list("foo, bar") == ["foo", "bar"]
        assert get_list('foo_"bar, baz') == ['foo_"bar', "baz"]
        assert get_list('"foo", "bar"') == ["foo", "bar"]
        assert get_list(u"foo, bar") == ["foo", "bar"]
        assert get_list(["foo", "bar"]) == ["foo", "bar"]
        assert get_list([u"foo", u"bar"]) == ["foo", "bar"]
        assert get_list(["foo", ["bar", "baz"]]) == ["foo", ["bar", "baz"]]

    def test_is_single_statement(self):
        singles = [
            "SELECT * FROM footable",
            'SELECT * FROM "bartable"',
            'SELECT * FROM "bartable";',
            'SELECT * FROM "bart;able";',
            "select 'foo'||chr(59)||'bar'",
            r"""SELECT ' \'' as A, * FROM "foo"; SELECT * FROM "abc" --'""",
        ]

        multiples = [
            "SELECT * FROM abc; SET LOCAL statement_timeout to",
            "SET LOCAL statement_timeout to; SELECT * FROM abc",
            'SELECT * FROM "foo"; SELECT * FROM "abc"',
        ]

        for single in singles:
            assert postgres_backend.is_single_statement(single) is True

        for multiple in multiples:
            assert postgres_backend.is_single_statement(multiple) is False

    @pytest.mark.ckan_config(
        "ckan.datastore.default_fts_index_field_types", "text tsvector")
    def test_should_fts_index_field_type(self):
        indexable_field_types = ["tsvector", "text"]

        non_indexable_field_types = [
            "nested",
            "timestamp",
            "date",
            "_text",
            "text[]",
        ]

        for indexable in indexable_field_types:
            assert (
                datastore_helpers.should_fts_index_field_type(indexable)
                is True
            )

        for non_indexable in non_indexable_field_types:
            assert (
                datastore_helpers.should_fts_index_field_type(non_indexable)
                is False
            )
