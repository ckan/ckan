import json
import nose
import pprint

import pylons
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests as tests

import ckanext.datastore.db as db
from ckanext.datastore.tests.helpers import extract, rebuild_all_dbs


class TestDatastoreSearch(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
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

        engine = db._get_engine(
                {'connection_url': pylons.config['ckan.datastore.write_url']}
            )
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)
        p.unload('datastore')

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

    def test_search_array_filters(self):
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
        assert result['records'] == [self.expected_records[0]]

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
                # invalid because author is not an array
                'filters': {u'author': [u'tolstoy']}}
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
        assert res_dict['error']['sort'][0] == u'field "f\xfc\xfc" not in table'

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

        expected_fields = [{u'type': u'int4', u'id': u'_id'},
                        {u'type': u'text', u'id': u'b\xfck'},
                        {u'type': u'text', u'id': u'author'},
                        {u'type': u'timestamp', u'id': u'published'},
                        {u'type': u'json', u'id': u'nested'},
                        {u'type': u'float4', u'id': u'rank'}]
        for field in expected_fields:
            assert field in result['fields'], field

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

    def test_search_table_metadata(self):
        data = {'resource_id': "_table_metadata"}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True


class TestDatastoreFullTextSearch(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
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
              {'id': 0, 'date': '2011-01-01', 'x': 1, 'y': 2, 'z': 3, 'country': 'DE', 'title': 'first', 'lat':52.56, 'lon':13.40},
              {'id': 1, 'date': '2011-02-02', 'x': 2, 'y': 4, 'z': 24, 'country': 'UK', 'title': 'second', 'lat':54.97, 'lon':-1.60},
              {'id': 2, 'date': '2011-03-03', 'x': 3, 'y': 6, 'z': 9, 'country': 'US', 'title': 'third', 'lat':40.00, 'lon':-75.5},
              {'id': 3, 'date': '2011-04-04', 'x': 4, 'y': 8, 'z': 6, 'country': 'UK', 'title': 'fourth', 'lat':57.27, 'lon':-6.20},
              {'id': 4, 'date': '2011-05-04', 'x': 5, 'y': 10, 'z': 15, 'country': 'UK', 'title': 'fifth', 'lat':51.58, 'lon':0},
              {'id': 5, 'date': '2011-06-02', 'x': 6, 'y': 12, 'z': 18, 'country': 'DE', 'title': 'sixth', 'lat':51.04, 'lon':7.9}
            ]
        )
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.normal_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        p.unload('datastore')

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


class TestDatastoreSQL(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        plugin = p.load('datastore')
        if plugin.legacy_mode:
            # make sure we undo adding the plugin
            p.unload('datastore')
            raise nose.SkipTest("SQL tests are not supported in legacy mode")
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

        cls.expected_records = [{u'_full_text': u"'annakarenina':1 'b':3 'moo':4 'tolstoy':2",
                                 u'_id': 1,
                                 u'author': u'tolstoy',
                                 u'b\xfck': u'annakarenina',
                                 u'nested': [u'b', {u'moo': u'moo'}],
                                 u'published': u'2005-03-01T00:00:00'},
                                {u'_full_text': u"'b':3 'tolstoy':2 'warandpeac':1",
                                 u'_id': 2,
                                 u'author': u'tolstoy',
                                 u'b\xfck': u'warandpeace',
                                 u'nested': {u'a': u'b'},
                                 u'published': None}]
        cls.expected_join_results = [{u'first': 1, u'second': 1}, {u'first': 1, u'second': 2}]

        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_is_single_statement(self):
        singles = ['SELECT * FROM footable',
            'SELECT * FROM "bartable"',
            'SELECT * FROM "bartable";',
            "select 'foo'||chr(59)||'bar'"]

        for single in singles:
            assert db._is_single_statement(single) is True

        multiples = ['SELECT * FROM abc; SET LOCAL statement_timeout to'
            'SET LOCAL statement_timeout to; SELECT * FROM abc',
            'SELECT * FROM "foo"; SELECT * FROM "abc"']

        for multiple in multiples:
            assert db._is_single_statement(multiple) is False

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
        assert result['records'] == self.expected_records

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
        assert result['records'] == self.expected_records

    def test_self_join(self):
        query = '''
            select a._id as first, b._id as second
            from "{0}" AS a,
                 "{0}" AS b
            where a.author = b.author
            limit 2
            '''.format(self.data['resource_id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['records'] == self.expected_join_results

    def test_read_private(self):
        context = {
            'user': self.sysadmin_user.name,
            'model': model}
        data_dict = {
            'resource_id': self.data['resource_id'],
            'connection_url': pylons.config['ckan.datastore.write_url']}
        p.toolkit.get_action('datastore_make_private')(context, data_dict)
        query = 'SELECT * FROM "{0}"'.format(self.data['resource_id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Authorization Error'

        # make it public for the other tests
        p.toolkit.get_action('datastore_make_public')(context, data_dict)

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

    def test_making_resource_private_makes_datastore_private(self):
        group = self.dataset.get_groups()[0]
        context = {
            'user': self.sysadmin_user.name,
            'ignore_auth': True,
            'model': model}
        package = p.toolkit.get_action('package_create')(
            context,
            {'name': 'privatedataset2',
             'private': False,
             'owner_org': self.organization['id'],
             'groups': [{
                 'id': group.id
             }]})
        resource = p.toolkit.get_action('resource_create')(
            context,
            {'name': 'privateresource2',
             'url': 'https://www.example.co.uk/',
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

        # Test public resource
        query = 'SELECT * FROM "{0}"'.format(resource['id'])
        data = {'sql': query}
        postparams_sql = json.dumps(data)
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams_sql,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        # Make resource private
        package = p.toolkit.get_action('package_show')(
            context, {'id': package.get('id')})
        package['private'] = True
        package = p.toolkit.get_action('package_update')(context, package)

        # Test private
        res = self.app.post('/api/action/datastore_search_sql', params=postparams_sql,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Authorization Error'

        postparams = json.dumps({'resource_id': resource['id']})
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Authorization Error'

        # we should not be able to make the private resource it public
        postparams = json.dumps({'resource_id': resource['id']})
        res = self.app.post('/api/action/datastore_make_public', params=postparams,
                            extra_environ=auth, status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
        assert res_dict['error']['__type'] == 'Authorization Error'

        # Make resource public
        package = p.toolkit.get_action('package_show')(
            context, {'id': package.get('id')})
        package['private'] = False
        package = p.toolkit.get_action('package_update')(context, package)

        # Test public again
        res = self.app.post('/api/action/datastore_search_sql', params=postparams_sql,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

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
            postparams = json.dumps(data)
            res = self.app.post('/api/action/datastore_search_sql',
                                params=postparams,
                                status=403)
            res_dict = json.loads(res.body)
            assert res_dict['success'] is False
            assert res_dict['error']['__type'] == 'Authorization Error'
