import ckan.tests as tests
from ckan.logic import get_action
import ckan.model as model
import ckan.new_authz as new_authz
import json

INITIAL_TEST_CONFIG_PERMISSIONS = {
    'anon_create_dataset': False,
    'create_dataset_if_not_in_organization': False,
    'user_create_groups': False,
    'user_create_organizations': False,
    'user_delete_groups': False,
    'user_delete_organizations': False,
    'create_user_via_api': False,
    'create_unowned_dataset': False,
}


class TestAuth(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        admin_api = get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})['apikey']
        ## This is a mutable dict on the class level so tests can
        ## add apikeys as they go along
        cls.apikeys = {'sysadmin': admin_api, 'random_key': 'moo'}

        cls.old_perm = new_authz.CONFIG_PERMISSIONS.copy()
        new_authz.CONFIG_PERMISSIONS.update(INITIAL_TEST_CONFIG_PERMISSIONS)

    @classmethod
    def teardown_class(cls):
        new_authz.CONFIG_PERMISSIONS.update(cls.old_perm)
        model.repo.rebuild_db()

    def _call_api(self, action, data, user, status=None):
        params = '%s=1' % json.dumps(data)
        return self.app.post('/api/action/%s' % action,
                             params=params,
                             extra_environ={'Authorization': self.apikeys[user]},
                             status=status)

    def create_user(self, name):
        user = {'name': name,
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = self._call_api('user_create', user, 'sysadmin', 200)
        self.apikeys[name] = str(json.loads(res.body)['result']['apikey'])


class TestAuthOrgs(TestAuth):

    def test_01_create_users(self):
        # actual roles assigned later
        self.create_user('org_admin')
        self.create_user('no_org')
        self.create_user('org_editor')
        self.create_user('editor_wannabe')

        user = {'name': 'user_no_auth',
                'password': 'pass',
                'email': 'moo@moo.com'}

        self._call_api('user_create', user, 'random_key', 403)
        self._call_api('user_create', user, 'no_org', 403)

    def test_02_create_orgs(self):
        org = {'name': 'org_no_user'}
        self._call_api('organization_create', org, 'random_key', 403)
        self._call_api('organization_create', org, 'sysadmin')

        org = {'name': 'org_with_user'}
        self._call_api('organization_create', org, 'random_key', 403)
        self._call_api('organization_create', org, 'sysadmin')

        #no user should be able to create org
        org = {'name': 'org_should_not_be_created'}
        self._call_api('organization_create', org, 'org_admin', 403)

    def test_03_create_dataset_no_org(self):

        dataset = {'name': 'admin_create_no_org'}
        self._call_api('package_create', dataset, 'sysadmin', 409)

        dataset = {'name': 'should_not_be_created'}
        self._call_api('package_create', dataset, 'no_org', 403)

    def test_04_create_dataset_with_org(self):

        dataset = {'name': 'admin_create_with_user',
                   'owner_org': 'org_with_user'}
        self._call_api('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'sysadmin_create_no_user',
                   'owner_org': 'org_no_user'}
        self._call_api('package_create', dataset, 'sysadmin', 200)

        dataset = {'name': 'user_create_with_org',
                   'owner_org': 'org_with_user'}
        self._call_api('package_create', dataset, 'no_org', 403)

    def test_05_add_users_to_org(self):

        member = {'username': 'org_admin',
                  'role': 'admin',
                  'id': 'org_with_user'}
        self._call_api('organization_member_create', member, 'sysadmin')

        ## admin user should be able to add users now
        member = {'username': 'org_editor',
                  'role': 'editor',
                  'id': 'org_with_user'}
        self._call_api('organization_member_create', member, 'org_admin')

        ## admin user should be able to add users now
        ## editor should not be able to approve others as editors
        member = {'username': 'editor_wannabe',
                  'role': 'editor',
                  'id': 'org_with_user'}
        self._call_api('organization_member_create', member, 'org_editor', 403)

    def _add_datasets(self, user):

        #org admin/editor should be able to add dataset to org.
        dataset = {'name': user + '_dataset', 'owner_org': 'org_with_user'}
        self._call_api('package_create', dataset, user, 200)

        #not able to add dataset to org admin does not belong to.
        dataset = {'name': user + '_dataset_bad', 'owner_org': 'org_no_user'}
        self._call_api('package_create', dataset, user, 409)

        #admin not able to make dataset not owned by a org
        dataset = {'name': user + '_dataset_bad'}
        self._call_api('package_create', dataset, user, 409)

        #not able to add org to not existant org
        dataset = {'name': user + '_dataset_bad', 'owner_org': 'org_not_exist'}
        self._call_api('package_create', dataset, user, 409)

    def test_07_add_datasets(self):
        self._add_datasets('org_admin')
        self._add_datasets('org_editor')

    def _update_datasets(self, user):
        ##editor/admin should be able to update dataset
        dataset = {'id': 'org_editor_dataset', 'title': 'test'}
        self._call_api('package_update', dataset, user, 200)
        # editor/admin tries to change owner org
        dataset = {'id': 'org_editor_dataset', 'owner_org': 'org_no_user'}
        self._call_api('package_update', dataset, user, 409)
        # editor/admin tries to update dataset in different org
        dataset = {'id': 'sysadmin_create_no_user', 'title': 'test'}
        self._call_api('package_update', dataset, user, 403)
        #non existant owner org
        dataset = {'id': 'org_editor_dataset', 'owner_org': 'org_not_exist'}
        self._call_api('package_update', dataset, user, 409)

    def test_08_update_datasets(self):
        self._update_datasets('org_admin')
        self._update_datasets('org_editor')

    def _delete_datasets(self, user):
        #editor/admin should be able to update dataset
        dataset = {'id': 'org_editor_dataset'}
        self._call_api('package_delete', dataset, user, 200)
        #not able to delete dataset in org user does not belong to
        dataset = {'id': 'sysadmin_create_no_user'}
        self._call_api('package_delete', dataset, user, 403)

    def test_09_delete_datasets(self):
        self._delete_datasets('org_admin')
        self._delete_datasets('org_editor')

    def test_10_edit_org(self):
        org = {'id': 'org_no_user', 'title': 'test'}
        #change an org user does not belong to
        self._call_api('organization_update', org, 'org_editor', 403)
        self._call_api('organization_update', org, 'org_admin', 403)

        #change an org a user belongs to
        org = {'id': 'org_with_user', 'title': 'test'}
        self._call_api('organization_update', org, 'org_editor', 403)
        self._call_api('organization_update', org, 'org_admin', 200)

    def test_11_delete_org(self):
        org = {'id': 'org_no_user', 'title': 'test'}
        self._call_api('organization_delete', org, 'org_editor', 403)
        self._call_api('organization_delete', org, 'org_admin', 403)
        org = {'id': 'org_with_user'}
        self._call_api('organization_delete', org, 'org_editor', 403)
        self._call_api('organization_delete', org, 'org_admin', 403)


class TestAuthGroups(TestAuth):

    def test_01_create_groups(self):
        group = {'name': 'group_no_user'}
        self._call_api('group_create', group, 'random_key', 403)
        self._call_api('group_create', group, 'sysadmin')

        group = {'name': 'group_with_user'}
        self._call_api('group_create', group, 'random_key', 403)
        self._call_api('group_create', group, 'sysadmin')

    def test_02_add_users_to_group(self):
        self.create_user('org_admin')
        self.create_user('org_editor')
        self.create_user('org_editor_wannabe')
        self.create_user('no_group')

        member = {'username': 'org_admin',
                  'role': 'admin',
                  'id': 'group_with_user'}
        self._call_api('group_member_create', member, 'sysadmin')

        ## admin user should be able to add users now
        member = {'username': 'org_editor',
                  'role': 'editor',
                  'id': 'group_with_user'}
        self._call_api('group_member_create', member, 'org_admin')

        ## editor should not be able to approve others as editors
        member = {'username': 'org_editor_wannabe',
                  'role': 'editor',
                  'id': 'group_with_user'}
        self._call_api('group_member_create', member, 'org_editor', 403)

    def test_03_add_dataset_to_group(self):
        org = {'name': 'org'}
        self._call_api('organization_create', org, 'sysadmin')
        package = {'name': 'package_added_by_admin', 'owner_org': 'org'}
        self._call_api('package_create', package, 'sysadmin')
        package = {'name': 'package_added_by_editor', 'owner_org': 'org'}
        self._call_api('package_create', package, 'sysadmin')

        res = self._call_api('group_show',
                             {'id': 'group_with_user'},
                             'org_admin')
        group = json.loads(res.body)['result']
        self._call_api('group_update', group, 'no_group', 403)
        self._call_api('group_update', group, 'org_admin')

        group = {'id': 'group_with_user',
                 'packages': [{'id': 'package_added_by_admin'},
                              {'id': 'package_added_by_editor'}]}
        # org editor doesn't have edit rights
        self._call_api('group_update', group, 'org_editor', 403)

    def test_04_modify_group(self):
        res = self._call_api('group_show',
                             {'id': 'group_with_user'},
                             'org_admin')
        group = json.loads(res.body)['result']
        group.update({
            'title': 'moo',
            'packages': [{'id': 'package_added_by_admin'}]
        })
        self._call_api('group_update', group, 'org_admin')

        # need to think about this as is horrible may just let editor edit
        # group for this case even though spec says otherwise
        self._call_api('group_update', group, 'org_editor', 403)

    def test_05_delete_group(self):
        org = {'id': 'group_with_user'}
        self._call_api('group_delete', org, 'org_editor', 403)
        self._call_api('group_delete', org, 'org_admin', 403)
        org = {'id': 'group_with_user'}
        self._call_api('group_delete', org, 'org_editor', 403)
        self._call_api('group_delete', org, 'org_admin', 403)
