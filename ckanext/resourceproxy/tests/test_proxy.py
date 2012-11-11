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
from ckan.lib.dictization.model_dictize import resource_dictize

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

        # set the url to a static resource
        resource_dict = resource_dictize(testpackage.resources[0], {'model': model})
        resource_dict['url'] = 'http://0.0.0.0:50001/static/test.json'
        context = {
            'model': model,
            'session': model.Session,
            'user': model.User.get('testsysadmin').name
        }
        l.action.update.resource_update(context, resource_dict)

        testpackage = model.Package.get('annakarenina')
        assert testpackage.resources[0].url == resource_dict['url'], testpackage.resources[0].url

        cls.data_dict = {
            'resource': {
                'id': testpackage.resources[0].id,
                'url': testpackage.resources[0].url
            },
            'package': {
                'name': testpackage.name
            }
        }

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

        proxied_url = proxy.get_proxified_resource_url(self.data_dict)
        result = requests.get(proxied_url)
        assert result.status_code == 200, result.status_code
        assert "yes, I'm proxied" in result.content, result.content
