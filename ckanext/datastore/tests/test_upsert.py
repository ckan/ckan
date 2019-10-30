# encoding: utf-8

import json
import datetime

from nose.tools import assert_equal, assert_not_equal, assert_raises, assert_in

import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan.plugins.toolkit import ValidationError, NotAuthorized

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import (
    set_url_type, DatastoreFunctionalTestBase,
    when_was_last_analyze)


def _search(resource_id):
    return helpers.call_action(
        u'datastore_search',
        resource_id=resource_id)


class TestDatastoreUpsert(DatastoreFunctionalTestBase):
    # Test action 'datastore_upsert' with 'method': 'upsert'

    def test_upsert_requires_auth(self):
        resource = factories.Resource(url_type=u'datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id']
        }
        with assert_raises(NotAuthorized) as context:
            helpers.call_action(
                'datastore_upsert',
                context={'user': '', 'ignore_auth': False},
                **data)
        assert_in(u'Action datastore_upsert requires an authenticated user',
                  str(context.exception))

    def test_upsert_empty_fails(self):
        resource = factories.Resource(url_type=u'datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {}  # empty
        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u"'Missing value'",
                  str(context.exception))

    def test_basic_as_update(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '1',
                 'book': u'The boy',
                 'author': u'F Torres'}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['records'][0]['book'], 'The boy')
        assert_equal(search_result['records'][0]['author'], 'F Torres')

    def test_basic_as_insert(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '2',
                 'book': u'The boy',
                 'author': u'F Torres'}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 2)
        assert_equal(search_result['records'][0]['book'], u'El Niño')
        assert_equal(search_result['records'][1]['book'], u'The boy')

    def test_upsert_only_one_field(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '1',
                 'book': u'The boy'}],  # not changing the author
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['records'][0]['book'], 'The boy')
        assert_equal(search_result['records'][0]['author'], 'Torres')

    def test_field_types(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'b\xfck',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'},
                       {'id': 'characters', 'type': 'text[]'},
                       {'id': 'published'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                         'published': '2005-03-01',
                         'nested': ['b', {'moo': 'moo'}]},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                         'nested': {'a': 'b'}},
                        {'author': 'adams',
                         'characters': ['Arthur', 'Marvin'],
                         'nested': {'foo': 'bar'},
                         u'b\xfck': u'guide to the galaxy'}]
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'upsert',
            'records': [{
                'author': 'adams',
                'characters': ['Bob', 'Marvin'],
                'nested': {'baz': 3},
                u'b\xfck': u'guide to the galaxy'}]
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 3)
        assert_equal(search_result['records'][0]['published'],
                     u'2005-03-01T00:00:00')  # i.e. stored in db as datetime
        assert_equal(search_result['records'][2]['author'], 'adams')
        assert_equal(search_result['records'][2]['characters'],
                     ['Bob', 'Marvin'])
        assert_equal(search_result['records'][2]['nested'], {'baz': 3})

    def test_percent(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'bo%ok', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1%',
                 'bo%ok': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '1%',
                 'bo%ok': u'The % boy',
                 'author': u'F Torres'},
                {'id': '2%',
                 'bo%ok': u'Gu%ide',
                 'author': u'Adams'}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 2)
        assert_equal(search_result['records'][0]['bo%ok'], 'The % boy')
        assert_equal(search_result['records'][1]['bo%ok'], 'Gu%ide')

    def test_missing_key(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'id': '1',
                         'book': 'guide',
                         'author': 'adams'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {  # no key
                    'book': u'El Niño',
                    'author': 'Torres'}],
        }
        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'fields "id" are missing', str(context.exception))

    def test_non_existing_field(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'upsert',
            'records': [{'id': '1',
                         'dummy': 'tolkien'}]  # key not known
        }

        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'fields "dummy" do not exist', str(context.exception))

    def test_upsert_works_with_empty_list_in_json_field(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'}],
            'records': [
                {'id': '1',
                 'nested': {'foo': 'bar'}}
            ],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '1',
                 'nested': []}],  # empty list
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['records'][0]['nested'], [])

    def test_delete_field_value(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'upsert',
            'records': [
                {'id': '1',
                 'book': None}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['records'][0]['book'], None)
        assert_equal(search_result['records'][0]['author'], 'Torres')

    def test_upsert_doesnt_crash_with_json_field(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'json'},
                       {'id': 'author', 'type': 'text'}],
        }
        helpers.call_action('datastore_create', **data)
        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [
                {'id': '1',
                 'book': {'code': 'A', 'title': u'ñ'},
                 'author': 'tolstoy'}],
        }
        helpers.call_action('datastore_upsert', **data)

    def test_upsert_doesnt_crash_with_json_field_with_string_value(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'json'},
                       {'id': 'author', 'type': 'text'}],
        }
        helpers.call_action('datastore_create', **data)
        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [
                {'id': '1',
                 'book': u'ñ',
                 'author': 'tolstoy'}],
        }
        helpers.call_action('datastore_upsert', **data)

    def test_dry_run(self):
        ds = factories.Dataset()
        table = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'text'}],
            primary_key=u'spam')
        helpers.call_action(
            u'datastore_upsert',
            resource_id=table['resource_id'],
            records=[{u'spam': u'SPAM'}, {u'spam': u'EGGS'}],
            dry_run=True)
        result = helpers.call_action(
            u'datastore_search',
            resource_id=table['resource_id'])
        assert_equal(result['records'], [])

    def test_dry_run_type_error(self):
        ds = factories.Dataset()
        table = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'numeric'}],
            primary_key=u'spam')
        try:
            helpers.call_action(
                u'datastore_upsert',
                resource_id=table['resource_id'],
                records=[{u'spam': u'SPAM'}, {u'spam': u'EGGS'}],
                dry_run=True)
        except ValidationError as ve:
            assert_equal(
                ve.error_dict['records'],
                [u'invalid input syntax for type numeric: "SPAM"'])
        else:
            assert 0, 'error not raised'

    def test_dry_run_trigger_error(self):
        ds = factories.Dataset()
        helpers.call_action(
            u'datastore_function_create',
            name=u'spamexception_trigger',
            rettype=u'trigger',
            definition=u'''
                BEGIN
                IF NEW.spam != 'spam' THEN
                    RAISE EXCEPTION '"%"? Yeeeeccch!', NEW.spam;
                END IF;
                RETURN NEW;
                END;''')
        table = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'text'}],
            primary_key=u'spam',
            triggers=[{u'function': u'spamexception_trigger'}])
        try:
            helpers.call_action(
                u'datastore_upsert',
                resource_id=table['resource_id'],
                records=[{u'spam': u'EGGS'}],
                dry_run=True)
        except ValidationError as ve:
            assert_equal(ve.error_dict['records'],
                         [u'"EGGS"? Yeeeeccch!'])
        else:
            assert 0, 'error not raised'

    def test_calculate_record_count_is_false(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'fields': [{'id': 'name', 'type': 'text'},
                       {'id': 'age', 'type': 'text'}],
        }
        helpers.call_action('datastore_create', **data)
        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [{"name": "Sunita", "age": "51"},
                        {"name": "Bowan", "age": "68"}],
        }
        helpers.call_action('datastore_upsert', **data)
        last_analyze = when_was_last_analyze(resource['id'])
        assert_equal(last_analyze, None)

    def test_calculate_record_count(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'fields': [{'id': 'name', 'type': 'text'},
                       {'id': 'age', 'type': 'text'}],
        }
        helpers.call_action('datastore_create', **data)
        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [{"name": "Sunita", "age": "51"},
                        {"name": "Bowan", "age": "68"}],
            'calculate_record_count': True
        }
        helpers.call_action('datastore_upsert', **data)
        last_analyze = when_was_last_analyze(resource['id'])
        assert_not_equal(last_analyze, None)


class TestDatastoreInsert(DatastoreFunctionalTestBase):
    # Test action 'datastore_upsert' with 'method': 'insert'

    def test_basic_insert(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['fields'], [
            {u'id': '_id', u'type': 'int'},
            {u'id': u'id', u'type': u'text'},
            {u'id': u'book', u'type': u'text'},
            {u'id': u'author', u'type': u'text'}
        ])
        assert_equal(
            search_result['records'][0],
            {u'book':
             u'El Ni\xf1o',
             u'_id': 1,
             u'id': u'1',
             u'author': u'Torres'})

    def test_non_existing_field(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'insert',
            'records': [{'id': '1',
                         'dummy': 'tolkien'}]  # key not known
        }

        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'row "1" has extra keys "dummy"', str(context.exception))

    def test_key_already_exists(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': 'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'id': '1',
                         'book': 'guide',
                         'author': 'adams'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'method': 'insert',
            'records': [
                {'id': '1',  # already exists
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'duplicate key value violates unique constraint',
                  str(context.exception))


class TestDatastoreUpdate(DatastoreFunctionalTestBase):
    # Test action 'datastore_upsert' with 'method': 'update'

    def test_basic(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [
                {'id': '1',
                 'book': u'El Niño',
                 'author': 'Torres'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'update',
            'records': [
                {'id': '1',
                 'book': u'The boy'}],
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 1)
        assert_equal(search_result['records'][0]['book'], 'The boy')
        assert_equal(search_result['records'][0]['author'], 'Torres')

    def test_field_types(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'b\xfck',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'},
                       {'id': 'characters', 'type': 'text[]'},
                       {'id': 'published'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                         'published': '2005-03-01',
                         'nested': ['b', {'moo': 'moo'}]},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                         'nested': {'a': 'b'}},
                        {'author': 'adams',
                         'characters': ['Arthur', 'Marvin'],
                         'nested': {'foo': 'bar'},
                         u'b\xfck': u'guide to the galaxy'}]
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'update',
            'records': [{
                'author': 'adams',
                'characters': ['Bob', 'Marvin'],
                'nested': {'baz': 3},
                u'b\xfck': u'guide to the galaxy'}]
        }
        helpers.call_action('datastore_upsert', **data)

        search_result = _search(resource['id'])
        assert_equal(search_result['total'], 3)
        assert_equal(search_result['records'][2]['author'], 'adams')
        assert_equal(search_result['records'][2]['characters'],
                     ['Bob', 'Marvin'])
        assert_equal(search_result['records'][2]['nested'], {'baz': 3})

    def test_update_unspecified_key(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'update',
            'records': [{'author': 'tolkien'}]  # no id
        }

        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'fields "id" are missing', str(context.exception))

    def test_update_unknown_key(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'update',
            'records': [{'id': '1',  # unknown
                         'author': 'tolkien'}]
        }

        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'key "[\\\'1\\\']" not found', str(context.exception))

    def test_update_non_existing_field(self):
        resource = factories.Resource(url_type='datastore')
        data = {
            'resource_id': resource['id'],
            'force': True,
            'primary_key': u'id',
            'fields': [{'id': 'id', 'type': 'text'},
                       {'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'id': '1',
                         'book': 'guide'}],
        }
        helpers.call_action('datastore_create', **data)

        data = {
            'resource_id': resource['id'],
            'method': 'update',
            'records': [{'id': '1',
                         'dummy': 'tolkien'}]  # key not known
        }

        with assert_raises(ValidationError) as context:
            helpers.call_action('datastore_upsert', **data)
        assert_in(u'fields "dummy" do not exist', str(context.exception))
