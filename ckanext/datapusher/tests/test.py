import json
import httpretty
import nose
import sys
import datetime

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
        p.load('datapusher')
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
        p.unload('datapusher')

    def test_create_ckan_resource_in_package(self):
        package = model.Package.get('annakarenina')
        data = {
            'resource': {'package_id': package.id}
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=200)
        res_dict = json.loads(res.body)

        assert 'resource_id' in res_dict['result']
        assert len(model.Package.get('annakarenina').resources) == 3

        res = tests.call_action_api(
            self.app, 'resource_show', id=res_dict['result']['resource_id'])
        assert res['url'] == '/datastore/dump/' + res['id'], res

    @httpretty.activate
    def test_providing_res_with_url_calls_datapusher_correctly(self):
        pylons.config['datapusher.url'] = 'http://datapusher.ckan.org'
        httpretty.HTTPretty.register_uri(
            httpretty.HTTPretty.POST,
            'http://datapusher.ckan.org/job',
            content_type='application/json',
            body=json.dumps({'job_id': 'foo', 'job_key': 'bar'}))

        package = model.Package.get('annakarenina')

        tests.call_action_api(
            self.app, 'datastore_create', apikey=self.sysadmin_user.apikey,
            resource=dict(package_id=package.id, url='demo.ckan.org'))

        assert len(package.resources) == 4, len(package.resources)
        resource = package.resources[3]
        data = json.loads(httpretty.last_request().body)
        assert data['metadata']['resource_id'] == resource.id, data
        assert data['result_url'].endswith('/action/datapusher_hook'), data
        assert data['result_url'].startswith('http://'), data

    def test_cant_provide_resource_and_resource_id(self):
        package = model.Package.get('annakarenina')
        resource = package.resources[0]
        data = {
            'resource_id': resource.id,
            'resource': {'package_id': package.id}
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['error']['__type'] == 'Validation Error'

    @httpretty.activate
    def test_send_datapusher_creates_task(self):
        httpretty.HTTPretty.register_uri(
            httpretty.HTTPretty.POST,
            'http://datapusher.ckan.org/job',
            content_type='application/json',
            body=json.dumps({'job_id': 'foo', 'job_key': 'bar'}))

        package = model.Package.get('annakarenina')
        resource = package.resources[0]

        context = {
            'ignore_auth': True,
            'user': self.sysadmin_user.name
        }

        p.toolkit.get_action('datapusher_submit')(context, {
            'resource_id': resource.id
        })

        context.pop('task_status', None)

        task = p.toolkit.get_action('task_status_show')(context, {
            'entity_id': resource.id,
            'task_type': 'datapusher',
            'key': 'datapusher'
        })

        assert task['state'] == 'pending', task

    def _call_datapusher_hook(self, user):
        package = model.Package.get('annakarenina')
        resource = package.resources[0]

        context = {
            'user': self.sysadmin_user.name
        }

        p.toolkit.get_action('task_status_update')(context, {
            'entity_id': resource.id,
            'entity_type': 'resource',
            'task_type': 'datapusher',
            'key': 'datapusher',
            'value': '{"job_id": "my_id", "job_key":"my_key"}',
            'last_updated': str(datetime.datetime.now()),
            'state': 'pending'
        })

        data = {
            'status': 'success',
            'metadata': {
                'resource_id': resource.id
            }
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(user.apikey)}
        res = self.app.post('/api/action/datapusher_hook', params=postparams,
                            extra_environ=auth, status=200)
        print res.body
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        task = tests.call_action_api(
            self.app, 'task_status_show', entity_id=resource.id,
            task_type='datapusher', key='datapusher')

        assert task['state'] == 'success', task

        task = tests.call_action_api(
            self.app, 'task_status_show', entity_id=resource.id,
            task_type='datapusher', key='datapusher')

        assert task['state'] == 'success', task

    def test_datapusher_hook_sysadmin(self):

        self._call_datapusher_hook(self.sysadmin_user)

    def test_datapusher_hook_normal_user(self):

        self._call_datapusher_hook(self.normal_user)

    def test_datapusher_hook_no_metadata(self):
        data = {
            'status': 'success',
        }
        postparams = '%s=1' % json.dumps(data)

        self.app.post('/api/action/datapusher_hook', params=postparams,
                      status=409)

    def test_datapusher_hook_no_status(self):
        data = {
            'metadata': {'resource_id': 'res_id'},
        }
        postparams = '%s=1' % json.dumps(data)

        self.app.post('/api/action/datapusher_hook', params=postparams,
                      status=409)

    def test_datapusher_hook_no_resource_id_in_metadata(self):
        data = {
            'status': 'success',
            'metadata': {}
        }
        postparams = '%s=1' % json.dumps(data)

        self.app.post('/api/action/datapusher_hook', params=postparams,
                      status=409)
