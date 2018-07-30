# encoding: utf-8

import json
import nose
import urllib
import pprint

import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests.legacy as tests

from ckan.common import config
import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import (
    extract, rebuild_all_dbs,
    DatastoreFunctionalTestBase, DatastoreLegacyTestBase)

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_in = nose.tools.assert_in


class TestDatastoreSearchNewTest(DatastoreFunctionalTestBase):
    def test_fts_on_field_calculates_ranks_only_on_that_specific_field(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'from': 'Brazil', 'to': 'Brazil'},
                {'from': 'Brazil', 'to': 'Italy'}
            ],
        }
        result = helpers.call_action('datastore_create', **data)
        search_data = {
            'resource_id': resource['id'],
            'fields': 'from',
            'q': {
                'from': 'Brazil'
            },
        }
        result = helpers.call_action('datastore_search', **search_data)
        ranks = [r['rank from'] for r in result['records']]
        assert_equals(len(result['records']), 2)
        assert_equals(len(set(ranks)), 1)

    def test_fts_works_on_non_textual_fields(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'from': 'Brazil', 'year': {'foo': 2014}},
                {'from': 'Brazil', 'year': {'foo': 1986}}
            ],
        }
        result = helpers.call_action('datastore_create', **data)

        search_data = {
            'resource_id': resource['id'],
            'fields': 'year',
            'plain': False,
            'q': {
                'year': '20:*'
            },
        }
        result = helpers.call_action('datastore_search', **search_data)
        assert_equals(len(result['records']), 1)
        assert_equals(result['records'][0]['year'], {'foo': 2014})

    def test_all_params_work_with_fields_with_whitespaces(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'the year': 2014},
                {'the year': 2013},
            ],
        }
        result = helpers.call_action('datastore_create', **data)
        search_data = {
            'resource_id': resource['id'],
            'fields': 'the year',
            'sort': 'the year',
            'filters': {
                'the year': 2013
            },
            'q': {
                'the year': '2013'
            },
        }
        result = helpers.call_action('datastore_search', **search_data)
        result_years = [r['the year'] for r in result['records']]
        assert_equals(result_years, [2013])



class TestDatastoreSearch(DatastoreLegacyTestBase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreSearch, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.dataset = model.Package.get('annakarenina')
        cls.resource = cls.dataset.resources[0]
        cls.data = {
            'resource_id': cls.resource.id,
            'force': True,
            'aliases': 'books3',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'},
                       {'id': u'characters', u'type': u'_text'},
                       {'id': 'rating with %'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                        'published': '2005-03-01', 'nested': ['b', {'moo': 'moo'}],
                        u'characters': [u'Princess Anna', u'Sergius'],
                        'rating with %': '60%'},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                        'nested': {'a': 'b'}, 'rating with %': '99%'}
                       ]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        # Make an organization, because private datasets must belong to one.
        cls.organization = tests.call_action_api(
            cls.app, 'organization_create',
            name='test_org',
            apikey=cls.sysadmin_user.apikey)

        cls.expected_records = [{u'published': u'2005-03-01T00:00:00',
                                 u'_id': 1,
                                 u'nested': [u'b', {u'moo': u'moo'}],
                                 u'b\xfck': u'annakarenina',
                                 u'author': u'tolstoy',
                                 u'characters': [u'Princess Anna', u'Sergius'],
                                 u'rating with %': u'60%'},
                                {u'published': None,
                                 u'_id': 2,
                                 u'nested': {u'a': u'b'},
                                 u'b\xfck': u'warandpeace',
                                 u'author': u'tolstoy',
                                 u'characters': None,
                                 u'rating with %': u'99%'}]

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    def test_search_basic(self):
        data = {'resource_id': self.data['resource_id']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == self.expected_records, result['records']

        # search with parameter id should yield the same results
        data = {'id': self.data['resource_id']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == self.expected_records, result['records']

    def test_search_private_dataset(self):
        group = self.dataset.get_groups()[0]
        context = {
            'user': self.sysadmin_user.name,
            'ignore_auth': True,
            'model': model}
        package = p.toolkit.get_action('package_create')(
            context,
            {'name': 'privatedataset',
             'private': True,
             'owner_org': self.organization['id'],
             'groups': [{
                 'id': group.id
             }]})
        resource = p.toolkit.get_action('resource_create')(
            context,
            {'name': 'privateresource',
             'url': 'https://www.example.com/',
             'package_id': package['id']})

        postparams = '%s=1' % json.dumps({
            'resource_id': resource['id'],
            'force': True
        })
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        data = {'resource_id': resource['id']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_alias(self):
        data = {'resource_id': self.data['aliases']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict_alias = json.loads(res.body)
        result = res_dict_alias['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == self.expected_records, result['records']

    def test_search_invalid_field(self):
        data = {'resource_id': self.data['resource_id'],
                'fields': [{'id': 'bad'}]}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_fields(self):
        data = {'resource_id': self.data['resource_id'],
                'fields': [u'b\xfck']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == [{u'b\xfck': 'annakarenina'},
                                     {u'b\xfck': 'warandpeace'}], result['records']

        data = {'resource_id': self.data['resource_id'],
                'fields': u'b\xfck, author'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == [{u'b\xfck': 'annakarenina', 'author': 'tolstoy'},
                    {u'b\xfck': 'warandpeace', 'author': 'tolstoy'}], result['records']

    def test_search_distinct(self):
        data = {'resource_id': self.data['resource_id'],
                'fields': [u'author'],
                'distinct': True}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        assert result['records'] == [{u'author': 'tolstoy'}], result['records']

    def test_search_filters(self):
        data = {'resource_id': self.data['resource_id'],
                'filters': {u'b\xfck': 'annakarenina'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1
        assert result['records'] == [self.expected_records[0]]

    def test_search_filter_array_field(self):
        data = {'resource_id': self.data['resource_id'],
                'filters': {u'characters': [u'Princess Anna', u'Sergius']}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1
        assert_equals(result['records'], [self.expected_records[0]])

    def test_search_multiple_filters_on_same_field(self):
        data = {'resource_id': self.data['resource_id'],
                'filters': {
                    u'b\xfck': [u'annakarenina', u'warandpeace']
                }}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        assert_equals(result['records'], self.expected_records)

    def test_search_filter_normal_field_passing_multiple_values_in_array(self):
        data = {'resource_id': self.data['resource_id'],
                'filters': {u'b\xfck': [u'annakarenina', u'warandpeace']}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        assert result['records'] == self.expected_records, result['records']

    def test_search_filters_get(self):
        filters = {u'b\xfck': 'annakarenina'}
        res = self.app.get('/api/action/datastore_search?resource_id={0}&filters={1}'.format(
                    self.data['resource_id'], json.dumps(filters)))
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1
        assert result['records'] == [self.expected_records[0]]

    def test_search_invalid_filter(self):
        data = {'resource_id': self.data['resource_id'],
                # invalid because author is not a numeric field
                'filters': {u'author': 42}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_sort(self):
        data = {'resource_id': self.data['resource_id'],
                'sort': u'b\xfck asc, author desc'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2

        assert result['records'] == self.expected_records, result['records']

        data = {'resource_id': self.data['resource_id'],
                'sort': [u'b\xfck desc', '"author" asc']}
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2

        assert result['records'] == self.expected_records[::-1]

    def test_search_invalid(self):
        data = {'resource_id': self.data['resource_id'],
                'sort': u'f\xfc\xfc asc'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        error_msg = res_dict['error']['sort'][0]
        assert u'f\xfc\xfc' in error_msg, \
            'Expected "{0}" to contain "{1}"'.format(error_msg, u'f\xfc\xfc')

    def test_search_limit(self):
        data = {'resource_id': self.data['resource_id'],
                'limit': 1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        assert result['records'] == [self.expected_records[0]]

    def test_search_invalid_limit(self):
        data = {'resource_id': self.data['resource_id'],
                'limit': 'bad'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {'resource_id': self.data['resource_id'],
                'limit': -1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_offset(self):
        data = {'resource_id': self.data['resource_id'],
                'limit': 1,
                'offset': 1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        assert result['records'] == [self.expected_records[1]]

    def test_search_invalid_offset(self):
        data = {'resource_id': self.data['resource_id'],
                'offset': 'bad'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {'resource_id': self.data['resource_id'],
                'offset': -1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'q': 'annakarenina'}

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1

        results = [extract(result['records'][0], [
            u'_id', u'author', u'b\xfck', u'nested',
            u'published', u'characters', u'rating with %'])]
        assert results == [self.expected_records[0]], results['records']

        data = {'resource_id': self.data['resource_id'],
                'q': 'tolstoy'}
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 2
        results = [extract(
            record,
            [u'_id', u'author', u'b\xfck', u'nested',
             u'published', u'characters', u'rating with %']
        ) for record in result['records']]
        assert results == self.expected_records, result['records']

        expected_fields = [{u'type': u'int', u'id': u'_id'},
                        {u'type': u'text', u'id': u'b\xfck'},
                        {u'type': u'text', u'id': u'author'},
                        {u'type': u'timestamp', u'id': u'published'},
                        {u'type': u'json', u'id': u'nested'}]
        for field in expected_fields:
            assert_in(field, result['fields'])

        # test multiple word queries (connected with and)
        data = {'resource_id': self.data['resource_id'],
                'plain': True,
                'q': 'tolstoy annakarenina'}
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1
        results = [extract(
            result['records'][0],
            [u'_id', u'author', u'b\xfck', u'nested', u'published',
             u'characters', u'rating with %'])]
        assert results == [self.expected_records[0]], results['records']

        for field in expected_fields:
            assert field in result['fields'], field

    def test_search_full_text_on_specific_column(self):
        data = {'resource_id': self.data['resource_id'],
                'q': {u"b\xfck": "annakarenina"}
                }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        assert_equals(len(res_dict['result']['records']), 1)
        assert_equals(res_dict['result']['records'][0]['_id'],
                      self.expected_records[0]['_id'])

    def test_search_full_text_on_specific_column_even_if_q_is_a_json_string(self):
        data = {'resource_id': self.data['resource_id'],
                'q': u'{"b\xfck": "annakarenina"}'
                }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        assert_equals(len(res_dict['result']['records']), 1)
        assert_equals(res_dict['result']['records'][0]['_id'],
                      self.expected_records[0]['_id'])

    def test_search_full_text_invalid_field_name(self):
        data = {'resource_id': self.data['resource_id'],
                'q': {'invalid_field_name': 'value'}
                }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_full_text_invalid_field_value(self):
        data = {'resource_id': self.data['resource_id'],
                'q': {'author': ['invalid', 'value']}
                }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_table_metadata(self):
        data = {'resource_id': "_table_metadata"}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

    def test_search_is_unsuccessful_when_called_with_filters_not_as_dict(self):
        data = {
            'resource_id': self.data['resource_id'],
            'filters': 'the-filter'
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error'].get('filters') is not None, res_dict['error']

    def test_search_is_unsuccessful_when_called_with_invalid_filters(self):
        data = {
            'resource_id': self.data['resource_id'],
            'filters': {
                'invalid-column-name': 'value'
            }
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error'].get('filters') is not None, res_dict['error']

    def test_search_is_unsuccessful_when_called_with_invalid_fields(self):
        data = {
            'resource_id': self.data['resource_id'],
            'fields': [
                'invalid-column-name'
            ]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error'].get('fields') is not None, res_dict['error']


class TestDatastoreFullTextSearch(DatastoreLegacyTestBase):
    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreFullTextSearch, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = dict(
            resource_id=resource.id,
            force=True,
            fields=[
              {'id': 'id'},
              {'id': 'date', 'type':'date'},
              {'id': 'x'},
              {'id': 'y'},
              {'id': 'z'},
              {'id': 'country'},
              {'id': 'title'},
              {'id': 'lat'},
              {'id': 'lon'}
            ],
            records=[
              {'id': 0, 'date': '2011-01-01', 'x': 1, 'y': 2, 'z': 3, 'country': 'DE', 'title': 'first 99', 'lat':52.56, 'lon':13.40},
              {'id': 1, 'date': '2011-02-02', 'x': 2, 'y': 4, 'z': 24, 'country': 'UK', 'title': 'second', 'lat':54.97, 'lon':-1.60},
              {'id': 2, 'date': '2011-03-03', 'x': 3, 'y': 6, 'z': 9, 'country': 'US', 'title': 'third', 'lat':40.00, 'lon':-75.5},
              {'id': 3, 'date': '2011-04-04', 'x': 4, 'y': 8, 'z': 6, 'country': 'UK', 'title': 'fourth', 'lat':57.27, 'lon':-6.20},
              {'id': 4, 'date': '2011-05-04', 'x': 5, 'y': 10, 'z': 15, 'country': 'UK', 'title': 'fifth', 'lat':51.58, 'lon':0},
              {'id': 5, 'date': '2011-06-02', 'x': 6, 'y': 12, 'z': 18, 'country': 'DE', 'title': 'sixth 53.56', 'lat':51.04, 'lon':7.9}
            ]
        )
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.normal_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

    def test_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'q': 'DE'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 2, pprint.pformat(res_dict)

    def test_advanced_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'plain': 'False',
                'q': 'DE | UK'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 5, pprint.pformat(res_dict)

    def test_full_text_search_on_integers_within_text_strings(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '99'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 1, pprint.pformat(res_dict)

    def test_full_text_search_on_integers(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '4'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 3, pprint.pformat(res_dict)

    def test_full_text_search_on_decimal_within_text_strings(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '53.56'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 1, pprint.pformat(res_dict)

    def test_full_text_search_on_decimal(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '52.56'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 1, pprint.pformat(res_dict)

    def test_full_text_search_on_date(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '2011-01-01'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 1, pprint.pformat(res_dict)

    def test_full_text_search_on_json_like_string_succeeds(self):
        data = {'resource_id': self.data['resource_id'],
                'q': '"{}"'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'], pprint.pformat(res_dict)


class TestDatastoreSQL(DatastoreLegacyTestBase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreSQL, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.dataset = model.Package.get('annakarenina')
        resource = cls.dataset.resources[0]
        cls.data = {
            'resource_id': resource.id,
            'force': True,
            'aliases': 'books4',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'}],
            'records': [{u'b\xfck': 'annakarenina',
                        'author': 'tolstoy',
                        'published': '2005-03-01',
                        'nested': ['b', {'moo': 'moo'}]},
                        {u'b\xfck': 'warandpeace',
                        'author': 'tolstoy',
                        'nested': {'a': 'b'}}]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        # Make an organization, because private datasets must belong to one.
        cls.organization = tests.call_action_api(
            cls.app, 'organization_create',
            name='test_org',
            apikey=cls.sysadmin_user.apikey)

        cls.expected_records = [{u'_full_text': [u"'annakarenina'", u"'b'",
                                                 u"'moo'", u"'tolstoy'",
                                                 u"'2005'"],
                                 u'_id': 1,
                                 u'author': u'tolstoy',
                                 u'b\xfck': u'annakarenina',
                                 u'nested': [u'b', {u'moo': u'moo'}],
                                 u'published': u'2005-03-01T00:00:00'},
                                {u'_full_text': [u"'tolstoy'", u"'warandpeac'",
                                                 u"'b'"],
                                 u'_id': 2,
                                 u'author': u'tolstoy',
                                 u'b\xfck': u'warandpeace',
                                 u'nested': {u'a': u'b'},
                                 u'published': None}]
        cls.expected_join_results = [{u'first': 1, u'second': 1}, {u'first': 1, u'second': 2}]

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    def test_validates_sql_has_a_single_statement(self):
        sql = 'SELECT * FROM public."{0}"; SELECT * FROM public."{0}";'.format(self.data['resource_id'])
        assert_raises(p.toolkit.ValidationError,
                      helpers.call_action, 'datastore_search_sql', sql=sql)

    def test_works_with_semicolons_inside_strings(self):
        sql = 'SELECT * FROM public."{0}" WHERE "author" = \'foo; bar\''.format(self.data['resource_id'])
        helpers.call_action('datastore_search_sql', sql=sql)

    def test_invalid_statement(self):
        query = 'SELECT ** FROM foobar'
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_select_basic(self):
        query = 'SELECT * FROM "{0}"'.format(self.data['resource_id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert len(result['records']) == len(self.expected_records)
        for (row_index, row) in enumerate(result['records']):
            expected_row = self.expected_records[row_index]
            assert set(row.keys()) == set(expected_row.keys())
            for field in row:
                if field == '_full_text':
                    for ft_value in expected_row['_full_text']:
                        assert ft_value in row['_full_text']
                else:
                    assert row[field] == expected_row[field]

        # test alias search
        query = 'SELECT * FROM "{0}"'.format(self.data['aliases'])
        data = {'sql': query}
        postparams = json.dumps(data)
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict_alias = json.loads(res.body)

        assert result['records'] == res_dict_alias['result']['records']

    def test_select_where_like_with_percent(self):
        query = 'SELECT * FROM public."{0}" WHERE "author" LIKE \'tol%\''.format(self.data['resource_id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert len(result['records']) == len(self.expected_records)
        for (row_index, row) in enumerate(result['records']):
            expected_row = self.expected_records[row_index]
            assert set(row.keys()) == set(expected_row.keys())
            for field in row:
                if field == '_full_text':
                    for ft_value in expected_row['_full_text']:
                        assert ft_value in row['_full_text']
                else:
                    assert row[field] == expected_row[field]

    def test_self_join(self):
        query = '''
            select a._id as first, b._id as second
            from "{0}" AS a,
                 "{0}" AS b
            where a.author = b.author
            limit 2
            '''.format(self.data['resource_id'])
        data = urllib.urlencode({'sql': query})
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=data,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['records'] == self.expected_join_results

    def test_new_datastore_table_from_private_resource(self):
        # make a private CKAN resource
        group = self.dataset.get_groups()[0]
        context = {
            'user': self.sysadmin_user.name,
            'ignore_auth': True,
            'model': model}
        package = p.toolkit.get_action('package_create')(
            context,
            {'name': 'privatedataset',
             'private': True,
             'owner_org': self.organization['id'],
             'groups': [{
                 'id': group.id
             }]})
        resource = p.toolkit.get_action('resource_create')(
            context,
            {'name': 'privateresource',
             'url': 'https://www.example.com/',
             'package_id': package['id']})

        postparams = '%s=1' % json.dumps({
            'resource_id': resource['id'],
            'force': True
        })
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        # new resource should be private
        query = 'SELECT * FROM "{0}"'.format(resource['id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Authorization Error'

    def test_not_authorized_to_access_system_tables(self):
        test_cases = [
            'SELECT * FROM pg_roles',
            'SELECT * FROM pg_catalog.pg_database',
            'SELECT rolpassword FROM pg_roles',
            '''SELECT p.rolpassword
               FROM pg_roles p
               JOIN "{0}" r
               ON p.rolpassword = r.author'''.format(self.data['resource_id']),
        ]
        for query in test_cases:
            data = {'sql': query.replace('\n', '')}
            postparams = urllib.urlencode(data)
            res = self.app.post('/api/action/datastore_search_sql',
                                params=postparams,
                                status=403)
            res_dict = json.loads(res.body)
            assert res_dict['success'] is False
            assert res_dict['error']['__type'] == 'Authorization Error'


class TestDatastoreSQLFunctional(DatastoreFunctionalTestBase):
    def test_search_sql_enforces_private(self):
        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        ctx1 = {u'user': user1['name'], u'ignore_auth': False}
        ctx2 = {u'user': user2['name'], u'ignore_auth': False}
        ctx3 = {u'user': user3['name'], u'ignore_auth': False}

        org1 = factories.Organization(
            user=user1,
            users=[{u'name': user3['name'], u'capacity': u'member'}])
        org2 = factories.Organization(
            user=user2,
            users=[{u'name': user3['name'], u'capacity': u'member'}])
        ds1 = factories.Dataset(owner_org=org1['id'], private=True)
        ds2 = factories.Dataset(owner_org=org2['id'], private=True)
        r1 = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds1['id']},
            fields=[{u'id': u'spam', u'type': u'text'}])
        r2 = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds2['id']},
            fields=[{u'id': u'ham', u'type': u'text'}])

        sql1 = 'SELECT spam FROM "{0}"'.format(r1['resource_id'])
        sql2 = 'SELECT ham FROM "{0}"'.format(r2['resource_id'])
        sql3 = 'SELECT spam, ham FROM "{0}", "{1}"'.format(
            r1['resource_id'], r2['resource_id'])

        assert_raises(
            p.toolkit.NotAuthorized,
            helpers.call_action,
            'datastore_search_sql',
            context=ctx2,
            sql=sql1)
        assert_raises(
            p.toolkit.NotAuthorized,
            helpers.call_action,
            'datastore_search_sql',
            context=ctx1,
            sql=sql2)
        assert_raises(
            p.toolkit.NotAuthorized,
            helpers.call_action,
            'datastore_search_sql',
            context=ctx1,
            sql=sql3)
        assert_raises(
            p.toolkit.NotAuthorized,
            helpers.call_action,
            'datastore_search_sql',
            context=ctx2,
            sql=sql3)
        helpers.call_action(
            'datastore_search_sql',
            context=ctx1,
            sql=sql1)
        helpers.call_action(
            'datastore_search_sql',
            context=ctx2,
            sql=sql2)
        helpers.call_action(
            'datastore_search_sql',
            context=ctx3,
            sql=sql3)


class TestDatastoreSearchRecordsFormat(DatastoreFunctionalTestBase):
    def test_sort_results_objects(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[
                {u'id': u'num', u'type': u'numeric'},
                {u'id': u'dt', u'type': u'timestamp'},
                {u'id': u'txt', u'type': u'text'}],
            records=[
                {u'num': 10, u'dt': u'2020-01-01', u'txt': 'aaab'},
                {u'num': 9, u'dt': u'2020-01-02', u'txt': 'aaab'},
                {u'num': 9, u'dt': u'2020-01-01', u'txt': 'aaac'}])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                sort=u'num, dt')['records'],
            [
                {u'_id': 3, u'num': 9, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaac'},
                {u'_id': 2, u'num': 9, u'dt': u'2020-01-02T00:00:00', u'txt': u'aaab'},
                {u'_id': 1, u'num': 10, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaab'},
            ])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                sort=u'dt, txt')['records'],
            [
                {u'_id': 1, u'num': 10, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaab'},
                {u'_id': 3, u'num': 9, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaac'},
                {u'_id': 2, u'num': 9, u'dt': u'2020-01-02T00:00:00', u'txt': u'aaab'},
            ])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                sort=u'txt, num')['records'],
            [
                {u'_id': 2, u'num': 9, u'dt': u'2020-01-02T00:00:00', u'txt': u'aaab'},
                {u'_id': 1, u'num': 10, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaab'},
                {u'_id': 3, u'num': 9, u'dt': u'2020-01-01T00:00:00', u'txt': u'aaac'},
            ])

    def test_sort_results_lists(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[
                {u'id': u'num', u'type': u'numeric'},
                {u'id': u'dt', u'type': u'timestamp'},
                {u'id': u'txt', u'type': u'text'}],
            records=[
                {u'num': 10, u'dt': u'2020-01-01', u'txt': u'aaab'},
                {u'num': 9, u'dt': u'2020-01-02', u'txt': u'aaab'},
                {u'num': 9, u'dt': u'2020-01-01', u'txt': u'aaac'}])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'lists',
                sort=u'num, dt')['records'],
            [
                [3, 9, u'2020-01-01T00:00:00', u'aaac'],
                [2, 9, u'2020-01-02T00:00:00', u'aaab'],
                [1, 10, u'2020-01-01T00:00:00', u'aaab'],
            ])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'lists',
                sort=u'dt, txt')['records'],
            [
                [1, 10, u'2020-01-01T00:00:00', u'aaab'],
                [3, 9, u'2020-01-01T00:00:00', u'aaac'],
                [2, 9, u'2020-01-02T00:00:00', u'aaab'],
            ])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'lists',
                sort=u'txt, num')['records'],
            [
                [2, 9, u'2020-01-02T00:00:00', u'aaab'],
                [1, 10, u'2020-01-01T00:00:00', u'aaab'],
                [3, 9, u'2020-01-01T00:00:00', u'aaac'],
            ])

    def test_sort_results_csv(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u'datastore_create',
            resource={u'package_id': ds['id']},
            fields=[
                {u'id': u'num', u'type': u'numeric'},
                {u'id': u'dt', u'type': u'timestamp'},
                {u'id': u'txt', u'type': u'text'}],
            records=[
                {u'num': 10, u'dt': u'2020-01-01', u'txt': u'aaab'},
                {u'num': 9, u'dt': u'2020-01-02', u'txt': u'aaab'},
                {u'num': 9, u'dt': u'2020-01-01', u'txt': u'aaac'}])
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'csv',
                sort=u'num, dt')['records'],
            u'3,9,2020-01-01T00:00:00,aaac\n'
            u'2,9,2020-01-02T00:00:00,aaab\n'
            u'1,10,2020-01-01T00:00:00,aaab\n'
            )
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'csv',
                sort=u'dt, txt')['records'],
            u'1,10,2020-01-01T00:00:00,aaab\n'
            u'3,9,2020-01-01T00:00:00,aaac\n'
            u'2,9,2020-01-02T00:00:00,aaab\n'
            )
        assert_equals(
            helpers.call_action(
                'datastore_search',
                resource_id=r['resource_id'],
                records_format=u'csv',
                sort=u'txt, num')['records'],
            u'2,9,2020-01-02T00:00:00,aaab\n'
            u'1,10,2020-01-01T00:00:00,aaab\n'
            u'3,9,2020-01-01T00:00:00,aaac\n'
            )
