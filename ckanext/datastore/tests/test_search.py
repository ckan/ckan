import json
import pprint

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
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'aliases': 'books3',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'},
                       {'id': u'characters', u'type': u'_text'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                        'published': '2005-03-01', 'nested': ['b', {'moo': 'moo'}],
                        u'characters': [u'Princess Anna', u'Sergius']},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                        'nested': {'a':'b'}}
                       ]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        cls.expected_records = [{u'published': u'2005-03-01T00:00:00',
                                 u'_id': 1,
                                 u'nested': [u'b', {u'moo': u'moo'}],
                                 u'b\xfck': u'annakarenina',
                                 u'author': u'tolstoy',
                                 u'characters': [u'Princess Anna', u'Sergius']},
                                {u'published': None,
                                 u'_id': 2,
                                 u'nested': {u'a': u'b'},
                                 u'b\xfck': u'warandpeace',
                                 u'author': u'tolstoy',
                                 u'characters': None}]

        import pylons
        engine = db._get_engine(
                None,
                {'connection_url': pylons.config['ckan.datastore.write_url']}
            )
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)

    def test_search_basic(self):
        data = {'resource_id': self.data['resource_id']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == len(self.data['records'])
        assert result['records'] == self.expected_records, result['records']

    def test_search_alias(self):
        data = {'resource_id': self.data['aliases']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_fields(self):
        data = {'resource_id': self.data['resource_id'],
                'fields': [u'b\xfck']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1
        assert result['records'] == [self.expected_records[0]]

    def test_search_sort(self):
        data = {'resource_id': self.data['resource_id'],
                'sort': u'b\xfck asc, author desc'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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

    def test_search_limit(self):
        data = {'resource_id': self.data['resource_id'],
                'limit': 1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_offset(self):
        data = {'resource_id': self.data['resource_id'],
                'limit': 1,
                'offset': 1}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'q': 'annakarenina'}

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['total'] == 1

        results = [extract(result['records'][0],
            [u'_id', u'author', u'b\xfck', u'nested', u'published', u'characters'])]
        assert results == [self.expected_records[0]], result['records']

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
                [u'_id', u'author', u'b\xfck', u'nested', u'published', u'characters']
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
                [u'_id', u'author', u'b\xfck', u'nested', u'published', u'characters']
            )]
        assert results == [self.expected_records[0]], result['records']

        for field in expected_fields:
            assert field in result['fields'], field

    def test_search_table_metadata(self):
        data = {'resource_id': "_table_metadata"}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True


class TestDatastoreFullTextSearch(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = dict(
            resource_id=resource.id,
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
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'q': 'DE'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 2, pprint.pformat(res_dict)

    def test_advanced_search_full_text(self):
        data = {'resource_id': self.data['resource_id'],
                'plain': 'False',
                'q': 'DE | UK'}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['total'] == 5, pprint.pformat(res_dict)


class TestDatastoreSQL(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
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
                        'nested': {'a':'b'}}
                       ]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

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

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

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
        query = 'SELECT ** FROM public.foobar'
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_select_basic(self):
        query = 'SELECT * FROM public."{0}"'.format(self.data['resource_id'])
        data = {'sql': query}
        postparams = json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['records'] == self.expected_records

        # test alias search
        query = 'SELECT * FROM public."{0}"'.format(self.data['aliases'])
        data = {'sql': query}
        postparams = json.dumps(data)
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict_alias = json.loads(res.body)

        assert result['records'] == res_dict_alias['result']['records']

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
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search_sql', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        result = res_dict['result']
        assert result['records'] == self.expected_join_results
