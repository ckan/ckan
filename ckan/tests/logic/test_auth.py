import ckan.tests as tests
from ckan.logic import get_action
import ckan.model as model
import ckan.new_authz as new_authz
import json
from ckan.tests import StatusCodes

INITIAL_TEST_CONFIG_PERMISSIONS = {
    'anon_create_dataset': False,
    'create_dataset_if_not_in_organization': False,
    'user_create_groups': False,
    'user_create_organizations': False,
    'create_user_via_api': False,
    'create_unowned_dataset': False,
}

new_authz.CONFIG_PERMISSIONS.update(INITIAL_TEST_CONFIG_PERMISSIONS)

class TestAction(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        admin_api = get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})['apikey']
        ## This is a mutable dict on the class level so tests can
        ## add apikeys as they go along
        cls.apikeys = {'sysadmin': admin_api, 'random_key': 'moo'}

        cls.old_perm = new_authz.CONFIG_PERMISSIONS
        new_authz.CONFIG_PERMISSIONS.update(INITIAL_TEST_CONFIG_PERMISSIONS)

    @classmethod
    def teardown_class(cls):
        new_authz.CONFIG_PERMISSIONS.update(cls.old_perm)
        model.repo.rebuild_db()

    def _action_post(self, action, data, user, status=None):
        params='%s=1' % json.dumps(data)
        return self.app.post('/api/action/%s' % action,
                             params=params,
                             extra_environ={'Authorization': self.apikeys[user]},
                             status=status)

    def test_1_create_orgs(self):
        org = {'name': 'org_no_user',}
        self._action_post('organization_create', org, 'random_key', 403)
        self._action_post('organization_create', org, 'sysadmin')

        org = {'name': 'org_with_user',}
        self._action_post('organization_create', org, 'random_key', 403)
        self._action_post('organization_create', org, 'sysadmin')

    def test_2_create_users(self):
        user = {'name': 'user_no_auth',
                'password': 'pass',
                'email': 'moo@moo.com'}

        self._action_post('user_create', user, 'random_key', 403)
        res = self._action_post('user_create', user, 'sysadmin')

        self.apikeys['no_org'] = str(json.loads(res.body)['result']['apikey'])

        self._action_post('user_create', user, 'no_org', 403)

    def test_3_create_dataset_no_org(self):

        dataset = {'name': 'admin_create_no_org'}
        res = self._action_post('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'should_not_be_created'}
        res = self._action_post('package_create', dataset, 'no_org', 403)

    def test_4_create_dataset_with_org(self):

        dataset = {'name': 'admin_create_with_org'}
        res = self._action_post('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'should_not_be_created2'}
        res = self._action_post('package_create', dataset, 'no_org', 403)

    def test_5_add_users_to_org(self):

        ## add admin user
        user = {'name': 'admin',
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = self._action_post('user_create', user, 'sysadmin')
        self.apikeys['admin'] = str(json.loads(res.body)['result']['apikey'])

        member = {'username': 'admin',
                  'role': 'admin',
                  'id': 'org_with_user'}
        self._action_post('organization_member_create', member, 'sysadmin')

        ## add editor user,
        user = {'name': 'editor',
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = self._action_post('user_create', user, 'sysadmin')
        self.apikeys['editor'] = str(json.loads(res.body)['result']['apikey'])

        ## admin user should be able to add users now
        member = {'username': 'editor',
                  'role': 'editor',
                  'id': 'org_with_user'}
        self._action_post('organization_member_create', member, 'admin')

        ## add disallowed editor.
        user = {'name': 'editor_wannabe',
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = self._action_post('user_create', user, 'sysadmin')
        self.apikeys['editor_wannabe'] = str(json.loads(res.body)['result']['apikey'])

        ## editor should not be able to approve others as editors
        member = {'username': 'editor_wannabe',
                  'role': 'editor',
                  'id': 'org_with_user'}
        self._action_post('organization_member_create', member, 'editor', 403)


    def test_6_admin_add_datasets(self):

        #org admin should be able to add dataset to group.
        dataset = {'name': 'admin_dataset', 'owner_org': 'org_with_user'}
        res = self._action_post('package_create', dataset, 'admin', 200)

        #not able to add dataset to org admin does not belong to.
        dataset = {'name': 'admin_dataset_bad', 'owner_org': 'org_no_user'}
        res = self._action_post('package_create', dataset, 'admin', 409)

        #admin not able to make dataset not owned by a group
        dataset = {'name': 'admin_dataset_bad' }
        res = self._action_post('package_create', dataset, 'admin', 409)

        #not able to add org to not existant group
        dataset = {'name': 'admin_dataset_bad', 'owner_org': 'org_not_exist' }
        res = self._action_post('package_create', dataset, 'admin', 409)

    def test_7_editor_add_datasets(self):
        ##same as admin
        dataset = {'name': 'editor_dataset', 'owner_org': 'org_with_user'}
        res = self._action_post('package_create', dataset, 'editor', 200)

        dataset = {'name': 'editor_dataset_bad', 'owner_org': 'org_no_user'}
        res = self._action_post('package_create', dataset, 'editor', 409)

        #no owner org
        dataset = {'name': 'editor_dataset_bad' }
        res = self._action_post('package_create', dataset, 'editor', 409)

        #non existant owner org
        dataset = {'name': 'admin_dataset_bad', 'owner_org': 'org_not_exist' }
        res = self._action_post('package_create', dataset, 'editor', 409)

    def test_8_editor_update_datasets(self):

        ##editor should be able to update dataset
        dataset = {'id': 'editor_dataset', 'title': 'test'}
        res = self._action_post('package_update', dataset, 'editor', 200)

        # editor tries to change owner org
        dataset = {'id': 'editor_dataset', 'owner_org': 'org_no_user'}
        res = self._action_post('package_update', dataset, 'editor', 409)

        #non existant owner org
        dataset = {'id': 'admin_dataset', 'owner_org': 'org_not_exist' }
        res = self._action_post('package_update', dataset, 'editor', 409)
