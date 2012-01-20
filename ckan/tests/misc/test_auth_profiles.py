from ckan.tests import *
import ckan.forms
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.package_saver import PackageSaver
from ckan.tests.pylons_controller import PylonsTestCase

class TestAuthProfiles(PylonsTestCase):

    @classmethod
    def setup_class(self):
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_authorizer_count(self):
        """ Ensure that we have the same number of auth functions in the 
            core auth profile as in the publisher auth profile """
            
        modules = {
            'ckan.logic.auth': 0,
            'ckan.logic.auth.publisher': 0
        }
        
        for module_root in modules.keys():
            print module_root
            for auth_module_name in ['get', 'create', 'update','delete']:
                module_path = '%s.%s' % (module_root, auth_module_name,)
                module = __import__(module_path)

                for part in module_path.split('.')[1:]:
                    module = getattr(module, part)
            
                for key, v in module.__dict__.items():
                    if not key.startswith('_'):
                        modules[module_root] = modules[module_root] + 1
        
        assert modules['ckan.logic.auth'] == modules['ckan.logic.auth.publisher']

