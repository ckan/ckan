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
        # redirect as not authorized
        response = self.app.get(url, status=[302])
        # random username
        response = self.app.get(url, status=[401],
                extra_environ={'REMOTE_USER': 'my-random-user-name'})
        # now test real access
        username = u'testsysadmin'.encode('utf8')
        response = self.app.get(url,
                extra_environ={'REMOTE_USER': username})
        assert 'Administration' in response, response

