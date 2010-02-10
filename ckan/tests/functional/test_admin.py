from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

# TODO: reenable these tests when we've worked out why it makes a few
# subsequent tests fail (in test_group and test_package).
class _TestAdminController(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()

        # setup a sysadmin        
        model.Session.add(model.User(name=u'testsysadmin'))        
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        testsysadmin = model.User.by_name(u'testsysadmin')
        model.add_user_to_role(testsysadmin, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

        self.testsysadmin = model.User.by_name(u'testsysadmin')

        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_index(self):
        user_name = self.testsysadmin.name
        response = self.app.get(url_for(controller='admin'), extra_environ={'REMOTE_USER': user_name.encode('utf8')})
        # Test response...
        assert 'Models' in response, response

    def test_package(self):
        user_name = self.testsysadmin.name
        url = url_for(controller='admin', action='Package')
        response = self.app.get(url, extra_environ={'REMOTE_USER': user_name.encode('utf8')}, status=200)
        # Test response...
        assert 'Package' in response, response
        assert 'Error' not in response

    def test_authz_ok(self):
        offset = url_for(controller='admin')
        user_name = self.testsysadmin.name
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user_name.encode('utf8')})
        assert 'Models' in res, res
        
    def test_authz_wrong_user(self):
        user_name = u'joebloggs'
        offset = url_for(controller='admin')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user_name.encode('utf8')}, status=[401])
        assert 'Models' not in res, res

    def test_authz_no_user(self):
        offset = url_for(controller='admin')
        res = self.app.get(offset, status=[401,302])
        assert 'Models' not in res, res
                
