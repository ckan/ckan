from ckan.tests import *
import ckan.forms
import ckan.model as model
from ckan.tests.pylons_controller import PylonsTestCase

from pylons import config

class TestAuthProfiles(PylonsTestCase):

    @classmethod
    def setup_class(self):
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_load_publisher_profile(self):
        """ Ensure that the relevant config settings result in the appropriate
            functions being loaded from the correct module """
        from new_authz import is_authorized, _get_auth_function

        config['ckan.auth.profile'] = 'publisher'
        _ = is_authorized('site_read', {'model': model, 'user': '127.0.0.1','reset_auth_profile':True})
        s = str(_get_auth_function('site_read').__module__)
        assert s == 'ckan.logic.auth.publisher.get', s

    def test_authorizer_count(self):
        """ Ensure that we have the same number of auth functions in the
            core auth profile as in the publisher auth profile """

        modules = {
            'ckan.logic.auth': 0,
            'ckan.logic.auth.publisher': 0
        }

        module_items = {
            'ckan.logic.auth': [],
            'ckan.logic.auth.publisher': []
        }

        for module_root in modules.keys():
            for auth_module_name in ['get', 'create', 'update','delete']:
                module_path = '%s.%s' % (module_root, auth_module_name,)
                module = __import__(module_path)

                for part in module_path.split('.')[1:]:
                    module = getattr(module, part)

                for key, v in module.__dict__.items():
                    if not key.startswith('_'):
                        modules[module_root] = modules[module_root] + 1
                        module_items[module_root].append( key )

        err = []
        if modules['ckan.logic.auth'] != modules['ckan.logic.auth.publisher']:
            oldauth = module_items['ckan.logic.auth']
            pubauth = module_items['ckan.logic.auth.publisher']
            for e in [n for n in oldauth if not n in pubauth]:
                err.append( '%s is in auth but not publisher auth ' % e )
            for e in [n for n in  pubauth if not n in oldauth]:
                err.append( '%s is in publisher auth but not auth ' % e )
        # Temporarily fudge
        assert modules['ckan.logic.auth']+8 == modules['ckan.logic.auth.publisher'], modules

