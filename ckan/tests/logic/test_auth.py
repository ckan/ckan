import mock

import ckan.tests as tests
from ckan.logic import get_action
import ckan.model as model
import ckan.new_authz as new_authz
from ckan.lib.create_test_data import CreateTestData
import json

INITIAL_TEST_CONFIG_PERMISSIONS = {
    'anon_create_dataset': False,
    'create_dataset_if_not_in_organization': False,
    'user_create_groups': False,
    'user_create_organizations': False,
    'user_delete_groups': False,
    'user_delete_organizations': False,
    'create_unowned_dataset': False,
    'create_user_via_api': False,
    'create_user_via_web': True,
    'roles_that_cascade_to_sub_groups': ['admin'],
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

    @classmethod
    def _call_api(cls, action, data, user, status=None):
        params = '%s=1' % json.dumps(data)
        res = cls.app.post('/api/action/%s' % action,
                            params=params,
                            extra_environ={'Authorization': cls.apikeys[user]},
                            status=[200, 403, 409])
        if res.status != (status or 200):
            error = json.loads(res.body)['error']
            raise AssertionError('Status was %s but should be %s. Error: %s' %
                                 (res.status, status, error))
        return res

    @classmethod
    def create_user(cls, name):
        user = {'name': name,
                'password': 'pass',
                'email': 'moo@moo.com'}
        res = cls._call_api('user_create', user, 'sysadmin', 200)
        cls.apikeys[name] = str(json.loads(res.body)['result']['apikey'])


class TestAuthUsers(TestAuth):
    def test_only_sysadmins_can_delete_users(self):
        username = 'username'
        user = {'id': username}
        self.create_user(username)

        self._call_api('user_delete', user, username, 403)
        self._call_api('user_delete', user, 'sysadmin', 200)

    def test_auth_deleted_users_are_always_unauthorized(self):
        always_success = lambda x,y: {'success': True}
        new_authz._AuthFunctions._build()
        new_authz._AuthFunctions._functions['always_success'] = always_success
        # We can't reuse the username with the other tests because we can't
        # rebuild_db(), because in the setup_class we get the sysadmin. If we
        # rebuild the DB, we would delete the sysadmin as well.
        username = 'deleted_user'
        self.create_user(username)
        user = model.User.get(username)
        user.delete()
        assert not new_authz.is_authorized_boolean('always_success', {'user': username})
        del new_authz._AuthFunctions._functions['always_success']


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

        # no owner_org supplied
        dataset = {'name': 'admin_create_no_org'}
        self._call_api('package_create', dataset, 'sysadmin', 409)

        dataset = {'name': 'should_not_be_created'}
        self._call_api('package_create', dataset, 'no_org', 403)

    def test_04_create_dataset_with_org(self):
        org_with_user = self._call_api('organization_show', {'id':
            'org_with_user'}, 'sysadmin')
        dataset = {'name': 'admin_create_with_user',
                   'owner_org': org_with_user.json['result']['id']}
        self._call_api('package_create', dataset, 'sysadmin', 200)

        org_no_user = self._call_api('organization_show', {'id':
            'org_no_user'}, 'sysadmin')
        dataset = {'name': 'sysadmin_create_no_user',
                   'owner_org': org_no_user.json['result']['id']}
        self._call_api('package_create', dataset, 'sysadmin', 200)
        dataset = {'name': 'user_create_with_org',
                   'owner_org': org_with_user.json['result']['id']}

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
        self._call_api('package_create', dataset, user, 403)

        #admin not able to make dataset not owned by a org
        dataset = {'name': user + '_dataset_bad'}
        self._call_api('package_create', dataset, user, 409)

        #not able to add org to not existant org
        dataset = {'name': user + '_dataset_bad', 'owner_org': 'org_not_exist'}
        self._call_api('package_create', dataset, user, 403)

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

ORG_HIERARCHY_PERMISSIONS = {
    'roles_that_cascade_to_sub_groups': ['admin'],
    }

class TestAuthOrgHierarchy(TestAuth):
    # Tests are in the same vein as TestAuthOrgs, testing the cases where the
    # group hierarchy provides extra permissions through cascading

    @classmethod
    def setup_class(cls):
        TestAuth.setup_class()
        CreateTestData.create_group_hierarchy_test_data()
        for user in model.Session.query(model.User):
            cls.apikeys[user.name] = str(user.apikey)
        new_authz.CONFIG_PERMISSIONS.update(ORG_HIERARCHY_PERMISSIONS)
        CreateTestData.create_arbitrary(
            package_dicts= [{'name': 'adataset',
                             'groups': ['national-health-service']}],
            extra_user_names=['john'])

    def _reset_a_datasets_owner_org(self):
        rev = model.repo.new_revision()
        get_action('package_owner_org_update')(
            {'model': model, 'ignore_auth': True},
            {'id': 'adataset',
             'organization_id': 'national-health-service'})

    def _undelete_package_if_needed(self, package_name):
        pkg = model.Package.by_name(package_name)
        if pkg and pkg.state == 'deleted':
            rev = model.repo.new_revision()
            pkg.state = 'active'
            model.repo.commit_and_remove()

    def test_05_add_users_to_org_1(self):
        member = {'username': 'john', 'role': 'admin',
                  'id': 'department-of-health'}
        self._call_api('organization_member_create', member, 'nhsadmin', 403)
    def test_05_add_users_to_org_2(self):
        member = {'username': 'john', 'role': 'editor',
                  'id': 'department-of-health'}
        self._call_api('organization_member_create', member, 'nhsadmin', 403)
    def test_05_add_users_to_org_3(self):
        member = {'username': 'john', 'role': 'admin',
                  'id': 'national-health-service'}
        self._call_api('organization_member_create', member, 'nhsadmin', 200)
    def test_05_add_users_to_org_4(self):
        member = {'username': 'john', 'role': 'editor',
                  'id': 'national-health-service'}
        self._call_api('organization_member_create', member, 'nhsadmin', 200)
    def test_05_add_users_to_org_5(self):
        member = {'username': 'john', 'role': 'admin',
                  'id': 'nhs-wirral-ccg'}
        self._call_api('organization_member_create', member, 'nhsadmin', 200)
    def test_05_add_users_to_org_6(self):
        member = {'username': 'john', 'role': 'editor',
                  'id': 'nhs-wirral-ccg'}
        self._call_api('organization_member_create', member, 'nhsadmin', 200)
    def test_05_add_users_to_org_7(self):
        member = {'username': 'john', 'role': 'editor',
                  'id': 'national-health-service'}
        self._call_api('organization_member_create', member, 'nhseditor', 403)

    def test_07_add_datasets_1(self):
        dataset = {'name': 't1', 'owner_org': 'department-of-health'}
        self._call_api('package_create', dataset, 'nhsadmin', 403)

    def test_07_add_datasets_2(self):
        dataset = {'name': 't2', 'owner_org': 'national-health-service'}
        self._call_api('package_create', dataset, 'nhsadmin', 200)

    def test_07_add_datasets_3(self):
        dataset = {'name': 't3', 'owner_org': 'nhs-wirral-ccg'}
        self._call_api('package_create', dataset, 'nhsadmin', 200)

    def test_07_add_datasets_4(self):
        dataset = {'name': 't4', 'owner_org': 'department-of-health'}
        self._call_api('package_create', dataset, 'nhseditor', 403)

    def test_07_add_datasets_5(self):
        dataset = {'name': 't5', 'owner_org': 'national-health-service'}
        self._call_api('package_create', dataset, 'nhseditor', 200)

    def test_07_add_datasets_6(self):
        dataset = {'name': 't6', 'owner_org': 'nhs-wirral-ccg'}
        self._call_api('package_create', dataset, 'nhseditor', 403)

    def test_08_update_datasets_1(self):
        dataset = {'name': 'adataset', 'owner_org': 'department-of-health'}
        self._call_api('package_update', dataset, 'nhsadmin', 409)

    def test_08_update_datasets_2(self):
        dataset = {'name': 'adataset', 'owner_org': 'national-health-service'}
        self._call_api('package_update', dataset, 'nhsadmin', 200)

    def test_08_update_datasets_3(self):
        dataset = {'name': 'adataset', 'owner_org': 'nhs-wirral-ccg'}
        try:
            self._call_api('package_update', dataset, 'nhsadmin', 200)
        finally:
            self._reset_a_datasets_owner_org()

    def test_08_update_datasets_4(self):
        dataset = {'name': 'adataset', 'owner_org': 'department-of-health'}
        self._call_api('package_update', dataset, 'nhseditor', 409)

    def test_08_update_datasets_5(self):
        dataset = {'name': 'adataset', 'owner_org': 'national-health-service'}
        try:
            self._call_api('package_update', dataset, 'nhseditor', 200)
        finally:
            self._reset_a_datasets_owner_org()

    def test_08_update_datasets_6(self):
        dataset = {'name': 'adataset', 'owner_org': 'nhs-wirral-ccg'}
        self._call_api('package_update', dataset, 'nhseditor', 409)

    def test_09_delete_datasets_1(self):
        dataset = {'id': 'doh-spend'}
        try:
            self._call_api('package_delete', dataset, 'nhsadmin', 403)
        finally:
            self._undelete_package_if_needed(dataset['id'])

    def test_09_delete_datasets_2(self):
        dataset = {'id': 'nhs-spend'}
        try:
            self._call_api('package_delete', dataset, 'nhsadmin', 200)
        finally:
            self._undelete_package_if_needed(dataset['id'])

    def test_09_delete_datasets_3(self):
        dataset = {'id': 'wirral-spend'}
        try:
            self._call_api('package_delete', dataset, 'nhsadmin', 200)
        finally:
            self._undelete_package_if_needed(dataset['id'])

    def test_09_delete_datasets_4(self):
        dataset = {'id': 'nhs-spend'}
        try:
            self._call_api('package_delete', dataset, 'nhseditor', 200)
        finally:
            self._undelete_package_if_needed(dataset['id'])

    def test_09_delete_datasets_5(self):
        dataset = {'id': 'wirral-spend'}
        try:
            self._call_api('package_delete', dataset, 'nhseditor', 403)
        finally:
            self._undelete_package_if_needed(dataset['id'])

    def _flesh_out_organization(self, org):
        # When calling organization_update, unless you include the list of
        # editor and admin users and parent groups, it will remove them. So
        # get the current list
        existing_org = get_action('organization_show')(
            {'model': model, 'ignore_auth': True}, {'id': org['id']})
        org.update(existing_org)

    def test_10_edit_org_1(self):
        org = {'id': 'department-of-health', 'title': 'test'}
        self._flesh_out_organization(org)
        self._call_api('organization_update', org, 'nhsadmin', 403)

    def test_10_edit_org_2(self):
        org = {'id': 'national-health-service', 'title': 'test'}
        self._flesh_out_organization(org)
        import pprint; pprint.pprint(org)
        print model.Session.query(model.Member).filter_by(state='deleted').all()
        self._call_api('organization_update', org, 'nhsadmin', 200)
        print model.Session.query(model.Member).filter_by(state='deleted').all()

    def test_10_edit_org_3(self):
        org = {'id': 'nhs-wirral-ccg', 'title': 'test'}
        self._flesh_out_organization(org)
        self._call_api('organization_update', org, 'nhsadmin', 200)

    def test_10_edit_org_4(self):
        org = {'id': 'department-of-health', 'title': 'test'}
        self._flesh_out_organization(org)
        self._call_api('organization_update', org, 'nhseditor', 403)

    def test_10_edit_org_5(self):
        org = {'id': 'national-health-service', 'title': 'test'}
        self._flesh_out_organization(org)
        self._call_api('organization_update', org, 'nhseditor', 403)

    def test_10_edit_org_6(self):
        org = {'id': 'nhs-wirral-ccg', 'title': 'test'}
        self._flesh_out_organization(org)
        self._call_api('organization_update', org, 'nhseditor', 403)

    def test_11_delete_org_1(self):
        org = {'id': 'department-of-health'}
        self._call_api('organization_delete', org, 'nhsadmin', 403)
        self._call_api('organization_delete', org, 'nhseditor', 403)

    def test_11_delete_org_2(self):
        org = {'id': 'national-health-service'}
        self._call_api('organization_delete', org, 'nhsadmin', 403)
        self._call_api('organization_delete', org, 'nhseditor', 403)

    def test_11_delete_org_3(self):
        org = {'id': 'nhs-wirral-ccg'}
        self._call_api('organization_delete', org, 'nhsadmin', 403)
        self._call_api('organization_delete', org, 'nhseditor', 403)


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
