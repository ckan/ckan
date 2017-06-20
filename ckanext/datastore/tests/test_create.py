# encoding: utf-8

import json
import nose
import sys
from nose.tools import assert_equal, raises

import sqlalchemy.orm as orm
import paste.fixture

from ckan.common import config
import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests.legacy as tests
import ckan.config.middleware as middleware
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import (
    rebuild_all_dbs, set_url_type, DatastoreFunctionalTestBase)
from ckan.plugins.toolkit import ValidationError


class TestDatastoreCreateNewTests(object):
    @classmethod
    def setup_class(cls):
        p.load('datastore')

    @classmethod
    def teardown_class(cls):
        p.unload('datastore')
        helpers.reset_db()

    def test_create_creates_index_on_primary_key(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'boo%k': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        index_names = self._get_index_names(resource_id)
        assert resource_id + '_pkey' in index_names

    def test_create_creates_url_with_site_name(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'boo%k': 'crime',
                'package_id': package['id']
            },
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        resource = helpers.call_action('resource_show', id=resource_id)
        url = resource['url']
        assert url.startswith(config.get('ckan.site_url'))

    def test_create_index_on_specific_fields(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'boo%k': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'indexes': ['author']
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        assert self._has_index_on_field(resource_id, '"author"')

    def test_create_adds_index_on_full_text_search_when_creating_other_indexes(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'boo%k': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'indexes': ['author']
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        assert self._has_index_on_field(resource_id, '"_full_text"')

    def test_create_adds_index_on_full_text_search_when_not_creating_other_indexes(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'boo%k': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        assert self._has_index_on_field(resource_id, '"_full_text"')

    def test_create_add_full_text_search_indexes_on_every_text_field(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'book': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
            'fields': [{'id': 'boo%k', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'lang': 'english',
        }
        result = helpers.call_action('datastore_create', **data)
        resource_id = result['resource_id']
        assert self._has_index_on_field(resource_id,
                                        "to_tsvector('english', \"boo%k\")")
        assert self._has_index_on_field(resource_id,
                                        "to_tsvector('english', \"author\")")

    def test_create_doesnt_add_more_indexes_when_updating_data(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'book': 'annakarenina', 'author': 'tolstoy'}
            ]
        }
        result = helpers.call_action('datastore_create', **data)
        previous_index_names = self._get_index_names(resource['id'])
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'book': 'warandpeace', 'author': 'tolstoy'}
            ]
        }
        result = helpers.call_action('datastore_create', **data)
        current_index_names = self._get_index_names(resource['id'])
        assert_equal(previous_index_names, current_index_names)

    @raises(p.toolkit.ValidationError)
    def test_create_duplicate_fields(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'book': 'crime',
                'author': ['tolstoy', 'dostoevsky'],
                'package_id': package['id']
            },
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'book', 'type': 'text'}],
        }
        result = helpers.call_action('datastore_create', **data)


    def _has_index_on_field(self, resource_id, field):
        sql = u"""
            SELECT
                relname
            FROM
                pg_class
            WHERE
                pg_class.relname = %s
            """
        index_name = db._generate_index_name(resource_id, field)
        results = self._execute_sql(sql, index_name).fetchone()
        return bool(results)

    def _get_index_names(self, resource_id):
        sql = u"""
            SELECT
                i.relname AS index_name
            FROM
                pg_class t,
                pg_class i,
                pg_index idx
            WHERE
                t.oid = idx.indrelid
                AND i.oid = idx.indexrelid
                AND t.relkind = 'r'
                AND t.relname = %s
            """
        results = self._execute_sql(sql, resource_id).fetchall()
        return [result[0] for result in results]

    def _execute_sql(self, sql, *args):
        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        return session.connection().execute(sql, *args)

    def test_sets_datastore_active_on_resource_on_create(self):
        resource = factories.Resource()

        assert_equal(resource['datastore_active'], False)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'book': 'annakarenina', 'author': 'tolstoy'}
            ]
        }

        helpers.call_action('datastore_create', **data)

        resource = helpers.call_action('resource_show', id=resource['id'])

        assert_equal(resource['datastore_active'], True)

    def test_sets_datastore_active_on_resource_on_delete(self):
        resource = factories.Resource(datastore_active=True)

        assert_equal(resource['datastore_active'], True)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'book': 'annakarenina', 'author': 'tolstoy'}
            ]
        }

        helpers.call_action('datastore_create', **data)

        helpers.call_action('datastore_delete', resource_id=resource['id'],
                            force=True)

        resource = helpers.call_action('resource_show', id=resource['id'])

        assert_equal(resource['datastore_active'], False)

    @raises(p.toolkit.ValidationError)
    def test_create_exceeds_column_name_limit(self):
        package = factories.Dataset()
        data = {
            'resource': {
                'package_id': package['id']
            },
            'fields': [{
                'id': 'This is a really long name for a column. Column names '
                'in Postgres have a limit of 63 characters',
                'type': 'text'
            }]
        }
        result = helpers.call_action('datastore_create', **data)


class TestDatastoreCreate(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):

        wsgiapp = middleware.make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))
        set_url_type(
            model.Package.get('annakarenina').resources, cls.sysadmin_user)

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_create_requires_auth(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_empty_fails(self):
        postparams = '%s=1' % json.dumps({})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_alias_name(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'aliases': u'foo"bar',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {
            'resource_id': resource.id,
            'aliases': u'fo%25bar',  # alias with percent
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_duplicate_alias_name(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'aliases': u'myalias'
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=200)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        # try to create another table with the same alias
        resource = model.Package.get('annakarenina').resources[1]
        data = {
            'resource_id': resource.id,
            'aliases': u'myalias'
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        # try to create an alias that is a resource id
        resource = model.Package.get('annakarenina').resources[1]
        data = {
            'resource_id': resource.id,
            'aliases': model.Package.get('annakarenina').resources[0].id
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_field_type(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'int['},  # this is invalid
                       {'id': 'author', 'type': 'INVALID'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_field_name(self):
        resource = model.Package.get('annakarenina').resources[0]
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        invalid_names = ['_author', '"author', '', ' author', 'author ',
                         '\tauthor', 'author\n']

        for field_name in invalid_names:
            data = {
                'resource_id': resource.id,
                'fields': [{'id': 'book', 'type': 'text'},
                           {'id': field_name, 'type': 'text'}]
            }
            postparams = '%s=1' % json.dumps(data)
            res = self.app.post('/api/action/datastore_create', params=postparams,
                                extra_environ=auth, status=409)
            res_dict = json.loads(res.body)
            assert res_dict['success'] is False

    def test_create_invalid_record_field(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        {'book': 'warandpeace', 'published': '1869'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_bad_records(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': ['bad']  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
        assert_equal(res_dict['error']['__type'], 'Validation Error')

        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        [],
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
        assert_equal(res_dict['error']['__type'], 'Validation Error')

    def test_create_invalid_index(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'indexes': 'book, dummy',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_unique_index(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'primary_key': 'dummy',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_alias_twice(self):
        resource = model.Package.get('annakarenina').resources[1]
        data = {
            'resource_id': resource.id,
            'aliases': 'new_alias',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True, res_dict

        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'aliases': 'new_alias',
            'fields': [{'id': 'more books', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False, res_dict

    def test_create_basic(self):
        resource = model.Package.get('annakarenina').resources[0]
        aliases = [u'great_list_of_books', u'another_list_of_b\xfcks']
        data = {
            'resource_id': resource.id,
            'aliases': aliases,
            'fields': [{'id': 'boo%k', 'type': 'text'},  # column with percent
                       {'id': 'author', 'type': 'json'}],
            'indexes': [['boo%k', 'author'], 'author'],
            'records': [{'boo%k': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'boo%k': 'annakarenina', 'author': ['tolstoy', 'putin']},
                        {'boo%k': 'warandpeace'}]  # treat author as null
        }
        ### Firstly test to see whether resource has no datastore table yet
        postparams = '%s=1' % json.dumps({'id': resource.id})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/resource_show', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['datastore_active'] is False

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True
        res = res_dict['result']
        assert res['resource_id'] == data['resource_id']
        assert res['fields'] == data['fields'], res['fields']
        assert res['records'] == data['records']

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('boo%k') == row['boo%k']
            assert data['records'][i].get('author') == (
                json.loads(row['author'][0]) if row['author'] else None)

        results = c.execute('''
            select * from "{0}" where _full_text @@ to_tsquery('warandpeace')
            '''.format(resource.id))
        assert results.rowcount == 1, results.rowcount

        results = c.execute('''
            select * from "{0}" where _full_text @@ to_tsquery('tolstoy')
            '''.format(resource.id))
        assert results.rowcount == 2
        self.Session.remove()

        # check aliases for resource
        c = self.Session.connection()
        for alias in aliases:

            results = [row for row in c.execute(u'select * from "{0}"'.format(resource.id))]
            results_alias = [row for row in c.execute(u'select * from "{0}"'.format(alias))]

            assert results == results_alias

            sql = u"select * from _table_metadata " \
                  "where alias_of=%s and name=%s"
            results = c.execute(sql, resource.id, alias)
            assert results.rowcount == 1
        self.Session.remove()

        # check to test to see if resource now has a datastore table
        postparams = '%s=1' % json.dumps({'id': resource.id})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/resource_show', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['datastore_active']

        #######  insert again simple
        data2 = {
            'resource_id': resource.id,
            'records': [{'boo%k': 'hagji murat', 'author': ['tolstoy']}]
        }

        postparams = '%s=1' % json.dumps(data2)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))
        self.Session.remove()

        assert results.rowcount == 4

        all_data = data['records'] + data2['records']
        for i, row in enumerate(results):
            assert all_data[i].get('boo%k') == row['boo%k']
            assert all_data[i].get('author') == (
                json.loads(row['author'][0]) if row['author'] else None)

        c = self.Session.connection()
        results = c.execute('''
            select * from "{0}" where _full_text @@ 'tolstoy'
            '''.format(resource.id))
        self.Session.remove()
        assert results.rowcount == 3

        #######  insert again extra field
        data3 = {
            'resource_id': resource.id,
            'records': [{'boo%k': 'crime and punsihment',
                         'author': ['dostoevsky'], 'rating': 2}],
            'indexes': ['rating']
        }

        postparams = '%s=1' % json.dumps(data3)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 5

        all_data = data['records'] + data2['records'] + data3['records']
        for i, row in enumerate(results):
            assert all_data[i].get('boo%k') == row['boo%k'], (i, all_data[i].get('boo%k'), row['boo%k'])
            assert all_data[i].get('author') == (json.loads(row['author'][0]) if row['author'] else None)

        results = c.execute('''select * from "{0}" where _full_text @@ to_tsquery('dostoevsky') '''.format(resource.id))
        self.Session.remove()
        assert results.rowcount == 2

        #######  insert again which will fail because of unique book name
        data4 = {
            'resource_id': resource.id,
            'records': [{'boo%k': 'warandpeace'}],
            'primary_key': 'boo%k'
        }

        postparams = '%s=1' % json.dumps(data4)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
        assert 'constraints' in res_dict['error'], res_dict

        #######  insert again which should not fail because constraint is removed
        data5 = {
            'resource_id': resource.id,
            'aliases': 'another_alias',  # replaces aliases
            'records': [{'boo%k': 'warandpeace'}],
            'primary_key': ''
        }

        postparams = '%s=1' % json.dumps(data5)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, expect_errors=True)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True, res_dict

        # new aliases should replace old aliases
        c = self.Session.connection()
        for alias in aliases:
            sql = "select * from _table_metadata " \
                  "where alias_of=%s and name=%s"
            results = c.execute(sql, resource.id, alias)
            assert results.rowcount == 0

        sql = "select * from _table_metadata " \
              "where alias_of=%s and name=%s"
        results = c.execute(sql, resource.id, 'another_alias')
        assert results.rowcount == 1
        self.Session.remove()

        #######  insert array type
        data6 = {
            'resource_id': resource.id,
            'fields': [{'id': 'boo%k', 'type': 'text'},
                       {'id': 'author', 'type': 'json'},
                       {'id': 'rating', 'type': 'int'},
                       {'id': 'characters', 'type': '_text'}],  # this is an array of strings
            'records': [{'boo%k': 'the hobbit',
                         'author': ['tolkien'], 'characters': ['Bilbo', 'Gandalf']}],
            'indexes': ['characters']
        }

        postparams = '%s=1' % json.dumps(data6)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, expect_errors=True)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True, res_dict

        #######  insert type that requires additional lookup
        data7 = {
            'resource_id': resource.id,
            'fields': [{'id': 'boo%k', 'type': 'text'},
                       {'id': 'author', 'type': 'json'},
                       {'id': 'rating', 'type': 'int'},
                       {'id': 'characters', 'type': '_text'},
                       {'id': 'location', 'type': 'int[2]'}],
            'records': [{'boo%k': 'lord of the rings',
                         'author': ['tolkien'], 'location': [3, -42]}],
            'indexes': ['characters']
        }

        postparams = '%s=1' % json.dumps(data7)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, expect_errors=True)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True, res_dict

        #######  insert with parameter id rather than resource_id which is a shortcut
        data8 = {
            'id': resource.id,
             # insert with percent
            'records': [{'boo%k': 'warandpeace', 'author': '99% good'}]
        }

        postparams = '%s=1' % json.dumps(data8)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, expect_errors=True)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True, res_dict

    def test_create_datastore_resource_on_dataset(self):
        pkg = model.Package.get('annakarenina')

        data = {
            'resource': {
                'package_id': pkg.id,
            },
            'fields': [{'id': 'boo%k', 'type': 'text'},  # column with percent
                       {'id': 'author', 'type': 'json'}],
            'indexes': [['boo%k', 'author'], 'author'],
            'records': [{'boo%k': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'boo%k': 'annakarenina', 'author': ['tolstoy', 'putin']},
                        {'boo%k': 'warandpeace'}]  # treat author as null
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True
        res = res_dict['result']
        assert res['fields'] == data['fields'], res['fields']
        assert res['records'] == data['records']

        # Get resource details
        data = {
            'id': res['resource_id']
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/resource_show', params=postparams)
        res_dict = json.loads(res.body)

        assert res_dict['result']['datastore_active'] is True


    def test_guess_types(self):
        resource = model.Package.get('annakarenina').resources[1]

        data = {
            'resource_id': resource.id
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth, status="*")  # ignore status
        res_dict = json.loads(res.body)

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'json'},
                       {'id': 'count'},
                       {'id': 'book'},
                       {'id': 'date'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 0.5},
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        c = self.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4', u'tsvector', u'nested', u'int4', u'text', u'timestamp', u'float8'], types

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('book') == row['book']
            assert data['records'][i].get('author') == (
                json.loads(row['author'][0]) if row['author'] else None)
        self.Session.remove()

        ### extend types

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'text'},
                       {'id': 'count'},
                       {'id': 'book'},
                       {'id': 'date'},
                       {'id': 'count2'},
                       {'id': 'extra', 'type':'text'},
                       {'id': 'date2'},
                      ],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2,
                         'nested': [1, 2], 'date2': '2005-12-01'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        c = self.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))
        self.Session.remove()

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4',  # id
                         u'tsvector',  # fulltext
                         u'nested',  # author
                         u'int4',  # count
                         u'text',  # book
                         u'timestamp',  # date
                         u'float8',  # count2
                         u'text',  # extra
                         u'timestamp',  # date2
                         u'nested',  # count3
                        ], types

        ### fields resupplied in wrong order

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'text'},
                       {'id': 'count'},
                       {'id': 'date'},  # date and book in wrong order
                       {'id': 'book'},
                       {'id': 'count2'},
                       {'id': 'extra', 'type':'text'},
                       {'id': 'date2'},
                      ],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2,
                         'count3': 432, 'date2': '2005-12-01'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_datastore_create_with_invalid_data_value(self):
        """datastore_create() should return an error for invalid data."""
        resource = factories.Resource(url_type="datastore")
        data_dict = {
            "resource_id": resource["id"],
            "fields": [{"id": "value", "type": "numeric"}],
            "records": [
                {"value": 0},
                {"value": 1},
                {"value": 2},
                {"value": 3},
                {"value": "   "},  # Invalid numeric value.
                {"value": 5},
                {"value": 6},
                {"value": 7},
            ],
            "method": "insert",
        }
        postparams = '%s=1' % json.dumps(data_dict)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Validation Error'
        assert res_dict['error']['message'].startswith('The data was invalid')


class TestDatastoreFunctionCreate(DatastoreFunctionalTestBase):
    def test_nop_trigger(self):
        helpers.call_action(
            u'datastore_function_create',
            name=u'test_nop',
            rettype=u'trigger',
            definition=u'BEGIN RETURN NEW; END;')

    def test_invalid_definition(self):
        try:
            helpers.call_action(
                u'datastore_function_create',
                name=u'test_invalid_def',
                rettype=u'trigger',
                definition=u'HELLO WORLD')
        except ValidationError as ve:
            assert_equal(
                ve.error_dict,
                {u'definition':
                    [u'syntax error at or near "HELLO"']})
        else:
            assert 0, u'no validation error'

    def test_redefined_trigger(self):
        helpers.call_action(
            u'datastore_function_create',
            name=u'test_redefined',
            rettype=u'trigger',
            definition=u'BEGIN RETURN NEW; END;')
        try:
            helpers.call_action(
                u'datastore_function_create',
                name=u'test_redefined',
                rettype=u'trigger',
                definition=u'BEGIN RETURN NEW; END;')
        except ValidationError as ve:
            assert_equal(
                ve.error_dict,
                {u'name':[
                    u'function "test_redefined" already exists '
                    u'with same argument types']})
        else:
            assert 0, u'no validation error'

    def test_redefined_with_or_replace_trigger(self):
        helpers.call_action(
            u'datastore_function_create',
            name=u'test_replaceme',
            rettype=u'trigger',
            definition=u'BEGIN RETURN NEW; END;')
        helpers.call_action(
            u'datastore_function_create',
            name=u'test_replaceme',
            or_replace=True,
            rettype=u'trigger',
            definition=u'BEGIN RETURN NEW; END;')


class TestDatastoreCreateTriggers(DatastoreFunctionalTestBase):
    def test_create_with_missing_trigger(self):
        ds = factories.Dataset()

        try:
            helpers.call_action(
                u'datastore_create',
                resource={u'package_id': ds['id']},
                fields=[{u'id': u'spam', u'type': u'text'}],
                records=[{u'spam': u'SPAM'}, {u'spam': u'EGGS'}],
                triggers=[{u'function': u'no_such_trigger_function'}])
        except ValidationError as ve:
            assert_equal(
                ve.error_dict,
                {u'triggers':[
                    u'function no_such_trigger_function() does not exist']})
        else:
            assert 0, u'no validation error'

    def test_create_trigger_applies_to_records(self):
        ds = factories.Dataset()

        helpers.call_action(
            u'datastore_function_create',
            name=u'spamify_trigger',
            rettype=u'trigger',
            definition=u'''
                BEGIN
                NEW.spam := 'spam spam ' || NEW.spam || ' spam';
                RETURN NEW;
                END;''')
        res = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'text'}],
            records=[{u'spam': u'SPAM'}, {u'spam': u'EGGS'}],
            triggers=[{u'function': u'spamify_trigger'}])
        assert_equal(
            helpers.call_action(
                u'datastore_search',
                fields=[u'spam'],
                resource_id=res['resource_id'])['records'],
            [
                {u'spam': u'spam spam SPAM spam'},
                {u'spam': u'spam spam EGGS spam'}])

    def test_upsert_trigger_applies_to_records(self):
        ds = factories.Dataset()

        helpers.call_action(
            u'datastore_function_create',
            name=u'more_spam_trigger',
            rettype=u'trigger',
            definition=u'''
                BEGIN
                NEW.spam := 'spam spam ' || NEW.spam || ' spam';
                RETURN NEW;
                END;''')
        res = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'text'}],
            triggers=[{u'function': u'more_spam_trigger'}])
        helpers.call_action(
            u'datastore_upsert',
            method=u'insert',
            resource_id=res['resource_id'],
            records=[{u'spam': u'BEANS'}, {u'spam': u'SPAM'}])
        assert_equal(
            helpers.call_action(
                u'datastore_search',
                fields=[u'spam'],
                resource_id=res['resource_id'])['records'],
            [
                {u'spam': u'spam spam BEANS spam'},
                {u'spam': u'spam spam SPAM spam'}])

    def test_create_trigger_exception(self):
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
        try:
            res = helpers.call_action(
                u'datastore_create',
                resource={u'package_id': ds['id']},
                fields=[{u'id': u'spam', u'type': u'text'}],
                records=[{u'spam': u'spam'}, {u'spam': u'EGGS'}],
                triggers=[{u'function': u'spamexception_trigger'}])
        except ValidationError as ve:
            assert_equal(
                ve.error_dict,
                {u'records':[
                    u'"EGGS"? Yeeeeccch!']})
        else:
            assert 0, u'no validation error'

    def test_upsert_trigger_exception(self):
        ds = factories.Dataset()

        helpers.call_action(
            u'datastore_function_create',
            name=u'spamonly_trigger',
            rettype=u'trigger',
            definition=u'''
                BEGIN
                IF NEW.spam != 'spam' THEN
                    RAISE EXCEPTION '"%"? Yeeeeccch!', NEW.spam;
                END IF;
                RETURN NEW;
                END;''')
        res = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[{u'id': u'spam', u'type': u'text'}],
            triggers=[{u'function': u'spamonly_trigger'}])
        try:
            helpers.call_action(
                u'datastore_upsert',
                method=u'insert',
                resource_id=res['resource_id'],
                records=[{u'spam': u'spam'}, {u'spam': u'BEANS'}])
        except ValidationError as ve:
            assert_equal(
                ve.error_dict,
                {u'records':[
                    u'"BEANS"? Yeeeeccch!']})
        else:
            assert 0, u'no validation error'
