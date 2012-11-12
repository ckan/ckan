import os
import json
import subprocess
import requests
import time

from nose.tools import assert_raises, assert_equal
import ckan.lib.helpers as h
import ckan.logic as l
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
from ckan.lib.create_test_data import CreateTestData

import ckanext.resourceproxy.plugin as proxy


class TestProxyBasic(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        static_files_server = os.path.join(os.path.dirname(__file__),
                                           'file_server.py')
        cls.static_files_server = subprocess.Popen(
            ['python', static_files_server])

        plugins.load('resourceproxy')

        # create test resource
        CreateTestData.create()
        testpackage = model.Package.get('annakarenina')

        context = {
            'model': model,
            'session': model.Session,
            'user': model.User.get('testsysadmin').name
        }

        # set the url to a static resource
        resource = l.get_action('resource_show')(context, {'id': testpackage.resources[0].id})
        package = l.get_action('package_show')(context, {'id': testpackage.id})

        resource['url'] = 'http://0.0.0.0:50001/static/test.json'
        l.action.update.resource_update(context, resource)

        testpackage = model.Package.get('annakarenina')
        assert testpackage.resources[0].url == resource['url'], testpackage.resources[0].url

        cls.data_dict = {'resource': resource, 'package': package}

        #make sure services are running
        for i in range(0, 50):
            time.sleep(0.1)
            response = requests.get('http://0.0.0.0:50001')
            if not response:
                continue
            return

        cls.teardown_class()
        raise Exception('services did not start!')

    @classmethod
    def teardown_class(cls):
        cls.static_files_server.kill()
        plugins.reset()

    def test_resource_proxy(self):
        url = self.data_dict['resource']['url']
        result = requests.get(url)
        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in result.content, result.content

        # fixme: there is a wrong url returned
        # strangely the before_map in the plugin is never called
        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        print proxied_url
        result = self.app.get(proxied_url)
        assert result.status == 200, result.status
        assert "yes, I'm proxied" in result.body, result.body
