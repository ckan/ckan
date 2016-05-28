# encoding: utf-8

import ckan.model as model
from ckan.tests.legacy import url_for, CreateTestData, WsgiAppCase

class TestAdminController(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        # setup test data including testsysadmin user
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    #test that only sysadmins can access the /ckan-admin page
    def test_index(self):
        url = url_for('ckanadmin', action='index')
        response = self.app.get(url, status=[403])
        # random username
        response = self.app.get(url, status=[403],
                extra_environ={'REMOTE_USER': 'my-random-user-name'})
        # now test real access
        username = u'testsysadmin'.encode('utf8')
        response = self.app.get(url,
                extra_environ={'REMOTE_USER': username})
        assert 'Administration' in response, response

