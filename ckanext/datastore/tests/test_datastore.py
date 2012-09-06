import unittest
import json
import sqlalchemy
import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests as tests
import ckanext.datastore.db as db
import pprint


def extract(d, keys):
    return dict((k, d[k]) for k in keys if k in d)


class TestTypeGetters(unittest.TestCase):
    def test_list(self):
        assert db._get_list(None) == None
        assert db._get_list([]) == []
        assert db._get_list('') == []
        assert db._get_list('foo') == ['foo']
        assert db._get_list('foo, bar') == ['foo', 'bar']
        assert db._get_list(u'foo, bar') == ['foo', 'bar']
        assert db._get_list(['foo', 'bar']) == ['foo', 'bar']
        assert db._get_list([u'foo', u'bar']) == ['foo', 'bar']
        assert db._get_list(['foo', ['bar', 'baz']]) == ['foo', ['bar', 'baz']]

    def test_bool(self):
        assert db._get_bool(None) == False
        assert db._get_bool(False) == False
        assert db._get_bool(True) == True
        assert db._get_bool('', True) == True
        assert db._get_bool('', False) == False
        assert db._get_bool('True') == True
        assert db._get_bool('False') == False
        assert db._get_bool('1') == True
        assert db._get_bool('0') == False
        assert db._get_bool('on') == True
        assert db._get_bool('off') == False


class TestDatastoreCreate(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None
    p.load('datastore')

    @classmethod
    def setup_class(cls):
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

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

    def test_create_invalid_field_type(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'INVALID'},
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
        data = {
            'resource_id': resource.id,
            'fields': [{'id': '_book', 'type': 'text'},
                       {'id': '_author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {
            'resource_id': resource.id,
            'fields': [{'id': '"book"', 'type': 'text'},
                       {'id': '"author', 'type': 'text'}]
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

    def test_create_basic(self):
        resource = model.Package.get('annakarenina').resources[0]
        alias = u'books1'
        data = {
            'resource_id': resource.id,
            'alias': alias,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': '_json'}],
            'primary_key': 'book, author',
            'indexes': ['author'],
            'records': [
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'book': 'annakarenina', 'author': ['tolstoy', 'putin']},
                        {'book': 'warandpeace'}]  # treat author as null
        }
        ### Firstly test to see if resource things it has datastore table
        postparams = '%s=1' % json.dumps({'id': resource.id})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/resource_show', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['datastore_active'] == False

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True
        assert res_dict['result']['resource_id'] == data['resource_id']
        assert res_dict['result']['fields'] == data['fields']
        assert res_dict['result']['records'] == data['records']

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('book') == row['book']
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
        model.Session.remove()

        # check alias for resource
        c = model.Session.connection()

        results = [row for row in c.execute('select * from "{0}"'.format(resource.id))]
        results_alias = [row for row in c.execute('select * from "{0}"'.format(alias))]

        assert results == results_alias

        sql = ("select * from _table_metadata "
            "where alias_of='{}' and name='{}'").format(resource.id, alias)
        results = c.execute(sql)
        assert results.rowcount == 1

        # check to test to see if resource now has a datastore table
        postparams = '%s=1' % json.dumps({'id': resource.id})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/resource_show', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['result']['datastore_active'] == True

        #######  insert again simple
        data2 = {
            'resource_id': resource.id,
            'records': [{'book': 'hagji murat', 'author': ['tolstoy']}]
        }

        postparams = '%s=1' % json.dumps(data2)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 4

        all_data = data['records'] + data2['records']
        for i, row in enumerate(results):
            assert all_data[i].get('book') == row['book']
            assert all_data[i].get('author') == (
                json.loads(row['author'][0]) if row['author'] else None)

        results = c.execute('''
            select * from "{0}" where _full_text @@ 'tolstoy'
            '''.format(resource.id))
        assert results.rowcount == 3
        model.Session.remove()

        #######  insert again extra field
        data3 = {
            'resource_id': resource.id,
            'records': [{'book': 'crime and punsihment',
                         'author': ['dostoevsky'], 'rating': 'good'}],
            'indexes': ['rating']
        }

        postparams = '%s=1' % json.dumps(data3)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 5

        all_data = data['records'] + data2['records'] + data3['records']
        for i, row in enumerate(results):
            assert all_data[i].get('book') == row['book'], (i, all_data[i].get('book'), row['book'])
            assert all_data[i].get('author') == (json.loads(row['author'][0]) if row['author'] else None)

        results = c.execute('''select * from "{0}" where _full_text @@ to_tsquery('dostoevsky') '''.format(resource.id))
        assert results.rowcount == 2

        model.Session.remove()

        #######  insert again which will fail because of unique book name
        data4 = {
            'resource_id': resource.id,
            'records': [{'book': 'warandpeace'}],
            'primary_key': 'book'
        }

        postparams = '%s=1' % json.dumps(data4)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
        assert 'constraints' in res_dict['error']

        #######  insert again which should not fail because constraint is removed
        data5 = {
            'resource_id': resource.id,
            'records': [{'book': 'warandpeace'}],
            'primary_key': ''
        }

        postparams = '%s=1' % json.dumps(data5)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, expect_errors=True)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

    def test_guess_types(self):
        resource = model.Package.get('annakarenina').resources[1]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': '_json'},
                       {'id': 'count'},
                       {'id': 'book'},
                       {'id': 'date'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2},
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        c = model.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4', u'tsvector', u'_json', u'int4',
                         u'text', u'timestamp', u'int4'], types

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('book') == row['book']
            assert data['records'][i].get('author') == (
                json.loads(row['author'][0]) if row['author'] else None)
        model.Session.remove()

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

        c = model.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4',  # id
                         u'tsvector',  # fulltext
                         u'_json',  # author
                         u'int4',  # count
                         u'text',  # book
                         u'timestamp',  # date
                         u'int4',  # count2
                         u'text',  # extra
                         u'timestamp',  # date2
                         u'_json',  # count3
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


class TestDatastoreUpsert(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None
    p.load('datastore')

    @classmethod
    def setup_class(cls):
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'alias': 'books3',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                        'published': '2005-03-01', 'nested': ['b', {'moo': 'moo'}]},
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

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_upsert_requires_auth(self):
        data = {
            'resource_id': self.data['resource_id']
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_upsert_empty_fails(self):
        postparams = '%s=1' % json.dumps({})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_insert(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'insert',
            'records': [{u'b\xfck': 'hagji murat', 'author': 'tolstoy'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))

        assert results.rowcount == 3


class TestDatastoreDelete(tests.WsgiAppCase):
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
            'alias': 'books2',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        {'book': 'warandpeace', 'author': 'tolstoy'}]
        }

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _create(self):
        postparams = '%s=1' % json.dumps(self.data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        return res_dict

    def _delete(self):
        data = {'resource_id': self.data['resource_id']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        assert res_dict['result'] == data
        return res_dict

    def test_delete_basic(self):
        self._create()
        self._delete()
        resource_id = self.data['resource_id']
        c = model.Session.connection()

        # alias should be deleted
        results = c.execute("select 1 from pg_views where viewname = '{}'".format(self.data['alias']))
        assert results.rowcount == 0

        try:
            # check that data was actually deleted: this should raise a
            # ProgrammingError as the table should not exist any more
            c.execute('select * from "{0}";'.format(resource_id))
            raise Exception("Data not deleted")
        except sqlalchemy.exc.ProgrammingError as e:
            expected_msg = 'relation "{}" does not exist'.format(resource_id)
            assert expected_msg in str(e)

        model.Session.remove()

    def test_delete_invalid_resource_id(self):
        postparams = '%s=1' % json.dumps({'resource_id': 'bad'})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth, status=404)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_delete_filters(self):
        self._create()
        resource_id = self.data['resource_id']

        # try and delete just the 'warandpeace' row
        data = {'resource_id': resource_id,
                'filters': {'book': 'warandpeace'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        c = model.Session.connection()
        result = c.execute('select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == 'annakarenina'
        model.Session.remove()

        # shouldn't delete anything
        data = {'resource_id': resource_id,
                'filters': {'book': 'annakarenina', 'author': 'bad'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        c = model.Session.connection()
        result = c.execute('select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == 'annakarenina'
        model.Session.remove()

        # delete the 'annakarenina' row
        data = {'resource_id': resource_id,
                'filters': {'book': 'annakarenina', 'author': 'tolstoy'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        c = model.Session.connection()
        result = c.execute('select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 0
        model.Session.remove()

        self._delete()


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
            'alias': 'books3',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'}],
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                        'published': '2005-03-01', 'nested': ['b', {'moo': 'moo'}]},
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
                                 u'nested':
                                    [u'b', {u'moo': u'moo'}],
                                    u'b\xfck': u'annakarenina',
                                    u'author': u'tolstoy'},
                                {u'published': None,
                                 u'_id': 2,
                                 u'nested':
                                    {u'a': u'b'},
                                    u'b\xfck': u'warandpeace',
                                    u'author': u'tolstoy'}]

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

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
        assert result['records'] == self.expected_records

        data = {'resource_id': self.data['alias']}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_search', params=postparams,
                            extra_environ=auth)
        res_dict_alias = json.loads(res.body)
        assert res_dict_alias['result']['records'] == res_dict['result']['records']

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
            [u'_id', u'author', u'b\xfck', u'nested', u'published'])]
        assert results == [self.expected_records[0]]

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
                [u'_id', u'author', u'b\xfck', u'nested', u'published']
            ) for record in result['records']]
        assert results == self.expected_records, result['records']

        expected_fields = [{u'type': u'int4', u'id': u'_id'},
                        {u'type': u'text', u'id': u'b\xfck'},
                        {u'type': u'text', u'id': u'author'},
                        {u'type': u'timestamp', u'id': u'published'},
                        {u'type': u'_json', u'id': u'nested'},
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
                [u'_id', u'author', u'b\xfck', u'nested', u'published']
            )]
        assert results == [self.expected_records[0]], result['records']

        for field in expected_fields:
            assert field in result['fields'], field


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
            'alias': 'books4',
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
            assert db.is_single_statement(single) is True

        multiples = ['SELECT * FROM abc; SET LOCAL statement_timeout to'
            'SET LOCAL statement_timeout to; SELECT * FROM abc',
            'SELECT * FROM "foo"; SELECT * FROM "abc"']

        for multiple in multiples:
            assert db.is_single_statement(multiple) is False

    def test_select_basic(self):
        query = 'SELECT * FROM public."{}"'.format(self.data['resource_id'])
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
        query = 'SELECT * FROM public."{}"'.format(self.data['alias'])
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
