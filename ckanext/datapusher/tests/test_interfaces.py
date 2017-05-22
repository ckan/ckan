# encoding: utf-8

import json
import httpretty
import nose
import sys
import datetime

from nose.tools import raises
from ckan.common import config
import sqlalchemy.orm as orm
import paste.fixture

from ckan.tests import helpers, factories
import ckan.plugins as p
import ckan.model as model
import ckan.tests.legacy as tests
import ckan.config.middleware as middleware

import ckanext.datapusher.interfaces as interfaces
import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import rebuild_all_dbs


# avoid hanging tests https://github.com/gabrielfalcao/HTTPretty/issues/34
if sys.version_info < (2, 7, 0):
    import socket
    socket.setdefaulttimeout(1)


class FakeDataPusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(interfaces.IDataPusher, inherit=True)

    def configure(self, config):
        self.after_upload_calls = 0

    def can_upload(self, resource_id):
        return False

    def after_upload(self, context, resource_dict, package_dict):
        self.after_upload_calls += 1


class TestInterace(object):
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
        p.load('test_datapusher_plugin')

        resource = factories.Resource(url_type='datastore')
        cls.dataset = factories.Dataset(resources=[resource])

        cls.sysadmin_user = factories.User(name='testsysadmin', sysadmin=True)
        cls.normal_user = factories.User(name='annafan')
        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)

        p.unload('datastore')
        p.unload('datapusher')
        p.unload('test_datapusher_plugin')

    @httpretty.activate
    @raises(p.toolkit.ObjectNotFound)
    def test_send_datapusher_creates_task(self):
        httpretty.HTTPretty.register_uri(
            httpretty.HTTPretty.POST,
            'http://datapusher.ckan.org/job',
            content_type='application/json',
            body=json.dumps({'job_id': 'foo', 'job_key': 'bar'}))

        resource = self.dataset['resources'][0]

        context = {
            'ignore_auth': True,
            'user': self.sysadmin_user['name']
        }

        result = p.toolkit.get_action('datapusher_submit')(context, {
            'resource_id': resource['id']
        })
        assert not result

        context.pop('task_status', None)

        # We expect this to raise a NotFound exception
        task = p.toolkit.get_action('task_status_show')(context, {
            'entity_id': resource['id'],
            'task_type': 'datapusher',
            'key': 'datapusher'
        })

    def test_after_upload_called(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        # Push data directly to the DataStore for the resource to be marked as
        # `datastore_active=True`, so the grid view can be created
        data = {
            'resource_id': resource['id'],
            'fields': [{'id': 'a', 'type': 'text'},
                       {'id': 'b', 'type': 'text'}],
            'records': [{'a': '1', 'b': '2'}, ],
            'force': True,
        }
        helpers.call_action('datastore_create', **data)

        # Create a task for `datapusher_hook` to update
        task_dict = {
            'entity_id': resource['id'],
            'entity_type': 'resource',
            'task_type': 'datapusher',
            'key': 'datapusher',
            'value': '{"job_id": "my_id", "job_key":"my_key"}',
            'last_updated': str(datetime.datetime.now()),
            'state': 'pending'
        }
        helpers.call_action('task_status_update', context={}, **task_dict)

        # Call datapusher_hook with a status of complete to trigger the
        # default views creation
        params = {
            'status': 'complete',
            'metadata': {'resource_id': resource['id']}
        }
        helpers.call_action('datapusher_hook', context={}, **params)

        total = sum(plugin.after_upload_calls for plugin
                    in p.PluginImplementations(interfaces.IDataPusher))
        assert total == 1, total

        params = {
            'status': 'complete',
            'metadata': {'resource_id': resource['id']}
        }
        helpers.call_action('datapusher_hook', context={}, **params)

        total = sum(plugin.after_upload_calls for plugin
                    in p.PluginImplementations(interfaces.IDataPusher))
        assert total == 2, total
