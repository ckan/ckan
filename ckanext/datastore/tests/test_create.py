import json
import httpretty
import nose
import sys
import datetime
from nose.tools import assert_equal

import pylons
from pylons import config
import sqlalchemy.orm as orm
import paste.fixture

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests as tests
import ckan.config.middleware as middleware

import ckanext.datastore.db as db
from ckanext.datastore.tests.helpers import rebuild_all_dbs, set_url_type


# avoid hanging tests https://github.com/gabrielfalcao/HTTPretty/issues/34
if sys.version_info < (2, 7, 0):
    import socket
    socket.setdefaulttimeout(1)


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
        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
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
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
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
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': '"author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': '', 'type': 'text'}]
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

            sql = (u"select * from _table_metadata "
                "where alias_of='{0}' and name='{1}'").format(resource.id, alias)
            results = c.execute(sql)
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
            sql = (u"select * from _table_metadata "
                "where alias_of='{0}' and name='{1}'").format(resource.id, alias)
            results = c.execute(sql)
            assert results.rowcount == 0

        sql = (u"select * from _table_metadata "
            "where alias_of='{0}' and name='{1}'").format(resource.id, 'another_alias')
        results = c.execute(sql)
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

