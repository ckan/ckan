# encoding: utf-8

import json
import nose
import datetime

import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests.legacy as tests
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckan.common import config

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import (
    set_url_type, DatastoreFunctionalTestBase, DatastoreLegacyTestBase)

assert_equal = nose.tools.assert_equal


class TestDatastoreUpsertNewTests(DatastoreFunctionalTestBase):
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


class TestDatastoreUpsert(DatastoreLegacyTestBase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreUpsert, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        set_url_type(
            model.Package.get('annakarenina').resources, cls.sysadmin_user)
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'},
                       {'id': 'characters', 'type': 'text[]'},
                       {'id': 'published'}],
            'primary_key': u'b\xfck',
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

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

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

    def test_upsert_basic(self):
        c = self.Session.connection()
        results = c.execute('select 1 from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 2
        self.Session.remove()

        hhguide = u"hitchhiker's guide to the galaxy"

        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{
                'author': 'adams',
                'nested': {'a': 2, 'b': {'c': 'd'}},
                'characters': ['Arthur Dent', 'Marvin'],
                'nested': {'foo': 'bar'},
                u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        assert records[2].characters == ['Arthur Dent', 'Marvin']
        assert json.loads(records[2].nested.json) == {'foo': 'bar'}
        self.Session.remove()

        c = self.Session.connection()
        results = c.execute("select * from \"{0}\" where author='{1}'".format(self.data['resource_id'], 'adams'))
        assert results.rowcount == 1
        self.Session.remove()

        # upsert only the publish date
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{'published': '1979-1-1', u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        assert records[2].published == datetime.datetime(1979, 1, 1)
        self.Session.remove()

        # delete publish date
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{u'b\xfck': hhguide, 'published': None}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        assert records[2].published == None
        self.Session.remove()

        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{'author': 'tolkien', u'b\xfck': 'the hobbit'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 4

        records = results.fetchall()
        assert records[3][u'b\xfck'] == 'the hobbit'
        assert records[3].author == 'tolkien'
        self.Session.remove()

        # test % in records
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{'author': 'tol % kien', u'b\xfck': 'the % hobbit'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

    def test_upsert_missing_key(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{'author': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_upsert_non_existing_field(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{u'b\xfck': 'annakarenina', 'dummy': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_upsert_works_with_empty_list_in_json_field(self):
        hhguide = u"hitchhiker's guide to the galaxy"

        data = {
            'resource_id': self.data['resource_id'],
            'method': 'upsert',
            'records': [{
                'nested': [],
                u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True, res_dict

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(data['resource_id']))
        record = [r for r in results.fetchall() if r[2] == hhguide]
        self.Session.remove()
        assert len(record) == 1, record
        assert_equal(json.loads(record[0][4].json),
                     data['records'][0]['nested'])



class TestDatastoreInsert(DatastoreLegacyTestBase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreInsert, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        set_url_type(
            model.Package.get('annakarenina').resources, cls.sysadmin_user)
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'},
                       {'id': 'characters', 'type': 'text[]'},
                       {'id': 'published'}],
            'primary_key': u'b\xfck',
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

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    def test_insert_non_existing_field(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'insert',
            'records': [{u'b\xfck': 'the hobbit', 'dummy': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_insert_with_index_violation(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'insert',
            'records': [{u'b\xfck': 'annakarenina'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_insert_basic(self):
        hhguide = u"hitchhiker's guide to the galaxy"
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'insert',
            'records': [{
                'author': 'adams',
                'characters': ['Arthur Dent', 'Marvin'],
                'nested': {'foo': 'bar', 'baz': 3},
                u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        self.Session.remove()

        assert results.rowcount == 3


class TestDatastoreUpdate(DatastoreLegacyTestBase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        super(TestDatastoreUpdate, cls).setup_class()
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        set_url_type(
            model.Package.get('annakarenina').resources, cls.sysadmin_user)
        resource = model.Package.get('annakarenina').resources[0]
        hhguide = u"hitchhiker's guide to the galaxy"
        cls.data = {
            'resource_id': resource.id,
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'nested', 'type': 'json'},
                       {'id': 'characters', 'type': 'text[]'},
                       {'id': 'published'}],
            'primary_key': u'b\xfck',
            'records': [{u'b\xfck': 'annakarenina', 'author': 'tolstoy',
                        'published': '2005-03-01', 'nested': ['b', {'moo': 'moo'}]},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                        'nested': {'a':'b'}},
                        {'author': 'adams',
                        'characters': ['Arthur Dent', 'Marvin'],
                        'nested': {'foo': 'bar'},
                        u'b\xfck': hhguide}
                       ]
            }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    def test_update_basic(self):
        c = self.Session.connection()
        results = c.execute('select 1 from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 3, results.rowcount
        self.Session.remove()

        hhguide = u"hitchhiker's guide to the galaxy"
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{
                'author': 'adams',
                'characters': ['Arthur Dent', 'Marvin'],
                'nested': {'baz': 3},
                u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        self.Session.remove()

        c = self.Session.connection()
        results = c.execute("select * from \"{0}\" where author='{1}'".format(self.data['resource_id'], 'adams'))
        assert results.rowcount == 1
        self.Session.remove()

        # update only the publish date
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{'published': '1979-1-1', u'b\xfck': hhguide}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        self.Session.remove()
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        assert records[2].published == datetime.datetime(1979, 1, 1)

        # delete publish date
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{u'b\xfck': hhguide, 'published': None}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = self.Session.connection()
        results = c.execute('select * from "{0}"'.format(self.data['resource_id']))
        self.Session.remove()
        assert results.rowcount == 3

        records = results.fetchall()
        assert records[2][u'b\xfck'] == hhguide
        assert records[2].author == 'adams'
        assert records[2].published == None

    def test_update_missing_key(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{'author': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_update_non_existing_key(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{u'b\xfck': '', 'author': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_update_non_existing_field(self):
        data = {
            'resource_id': self.data['resource_id'],
            'method': 'update',
            'records': [{u'b\xfck': 'annakarenina', 'dummy': 'tolkien'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_upsert', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False
