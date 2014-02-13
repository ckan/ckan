import json
import nose

import pylons
import sqlalchemy
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests as tests

import ckanext.datastore.db as db
from ckanext.datastore.tests.helpers import rebuild_all_dbs, set_url_type


class TestDatastoreDelete(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None
    Session = None

    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'aliases': u'b\xfck2',
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'rating with %', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'rating with %': '90%'},
                        {'book': 'warandpeace', 'author': 'tolstoy',
                         'rating with %': '42%'}]
        }

        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))
        set_url_type(
            model.Package.get('annakarenina').resources, cls.sysadmin_user)

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)
        p.unload('datastore')

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
        c = self.Session.connection()

        # It's dangerous to build queries as someone could inject sql.
        # It's okay here as it is a test but don't use it anyhwere else!
        results = c.execute(u"select 1 from pg_views where viewname = '{0}'".format(self.data['aliases']))
        assert results.rowcount == 0

        try:
            # check that data was actually deleted: this should raise a
            # ProgrammingError as the table should not exist any more
            c.execute(u'select * from "{0}";'.format(resource_id))
            raise Exception("Data not deleted")
        except sqlalchemy.exc.ProgrammingError as e:
            expected_msg = 'relation "{0}" does not exist'.format(resource_id)
            assert expected_msg in str(e)

        self.Session.remove()

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

        c = self.Session.connection()
        result = c.execute(u'select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == 'annakarenina'
        self.Session.remove()

        # shouldn't delete anything
        data = {'resource_id': resource_id,
                'filters': {'book': 'annakarenina', 'author': 'bad'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        c = self.Session.connection()
        result = c.execute(u'select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 1
        assert results[0].book == 'annakarenina'
        self.Session.remove()

        # delete the 'annakarenina' row and also only use id
        data = {'id': resource_id,
                'filters': {'book': 'annakarenina', 'author': 'tolstoy'}}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        c = self.Session.connection()
        result = c.execute(u'select * from "{0}";'.format(resource_id))
        results = [r for r in result]
        assert len(results) == 0
        self.Session.remove()

        self._delete()
