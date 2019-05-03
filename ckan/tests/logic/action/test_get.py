# encoding: utf-8

import datetime
import copy

import nose.tools

from six import text_type
from six.moves import xrange

from ckan import __version__
import ckan.logic as logic
import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic.schema as schema
from ckan.lib.search.common import SearchError


eq = nose.tools.eq_
ok = nose.tools.ok_
assert_not_in = nose.tools.assert_not_in
assert_raises = nose.tools.assert_raises


class TestPackageShow(helpers.FunctionalTestBase):

    def test_package_show(self):
        dataset1 = factories.Dataset()

        dataset2 = helpers.call_action('package_show', id=dataset1['id'])

        eq(dataset2['name'], dataset1['name'])
        missing_keys = set(('title', 'groups')) - set(dataset2.keys())
        assert not missing_keys, missing_keys

    def test_package_show_with_custom_schema(self):
        dataset1 = factories.Dataset()
        from ckan.logic.schema import default_show_package_schema
        custom_schema = default_show_package_schema()

        def foo(key, data, errors, context):
            data[key] = 'foo'
        custom_schema['new_field'] = [foo]

        dataset2 = helpers.call_action('package_show', id=dataset1['id'],
                                       context={'schema': custom_schema})

        eq(dataset2['new_field'], 'foo')

    def test_package_show_with_custom_schema_return_default_schema(self):
        dataset1 = factories.Dataset()
        from ckan.logic.schema import default_show_package_schema
        custom_schema = default_show_package_schema()

        def foo(key, data, errors, context):
            data[key] = 'foo'
        custom_schema['new_field'] = [foo]

        dataset2 = helpers.call_action('package_show', id=dataset1['id'],
                                       use_default_schema=True,
                                       context={'schema': custom_schema})

        assert 'new_field' not in dataset2


class TestGroupList(helpers.FunctionalTestBase):

    def test_group_list(self):

        group1 = factories.Group()
        group2 = factories.Group()

        group_list = helpers.call_action('group_list')

        assert (sorted(group_list) ==
                sorted([g['name'] for g in [group1, group2]]))

    def test_group_list_in_presence_of_organizations(self):
        '''
        Getting the group_list should only return groups of type 'group' (not
        organizations).
        '''
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Organization()
        factories.Organization()

        group_list = helpers.call_action('group_list')

        assert (sorted(group_list) ==
                sorted([g['name'] for g in [group1, group2]]))

    def test_group_list_in_presence_of_custom_group_types(self):
        '''Getting the group_list shouldn't return custom group types.'''
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Group(type='custom')

        group_list = helpers.call_action('group_list')

        assert (sorted(group_list) ==
                sorted([g['name'] for g in [group1, group2]]))

    def test_group_list_return_custom_group(self):
        '''
        Getting the group_list with a type defined should only return
        groups of that type.
        '''
        group1 = factories.Group(type='custom')
        group2 = factories.Group(type='custom')
        factories.Group()
        factories.Group()

        group_list = helpers.call_action('group_list', type='custom')

        assert (sorted(group_list) ==
                sorted([g['name'] for g in [group1, group2]]))

    def test_group_list_sort_by_package_count(self):

        factories.Group(name='aa')
        factories.Group(name='bb')
        factories.Dataset(groups=[{'name': 'aa'}, {'name': 'bb'}])
        factories.Dataset(groups=[{'name': 'bb'}])

        group_list = helpers.call_action('group_list', sort='package_count')
        eq(sorted(group_list), sorted(['bb', 'aa']))

    def test_group_list_sort_by_package_count_ascending(self):

        factories.Group(name='aa')
        factories.Group(name='bb')
        factories.Dataset(groups=[{'name': 'aa'}, {'name': 'bb'}])
        factories.Dataset(groups=[{'name': 'aa'}])

        group_list = helpers.call_action('group_list',
                                         sort='package_count asc')

        eq(group_list, ['bb', 'aa'])

    def eq_expected(self, expected_dict, result_dict):
        superfluous_keys = set(result_dict) - set(expected_dict)
        assert not superfluous_keys, 'Did not expect key: %s' % \
            ' '.join(('%s=%s' % (k, result_dict[k]) for k in superfluous_keys))
        for key in expected_dict:
            assert expected_dict[key] == result_dict[key], \
                '%s=%s should be %s' % \
                (key, result_dict[key], expected_dict[key])

    def test_group_list_all_fields(self):

        group = factories.Group()

        group_list = helpers.call_action('group_list', all_fields=True)

        expected_group = dict(group.items()[:])
        for field in ('users', 'tags', 'extras', 'groups'):
            del expected_group[field]

        assert group_list[0] == expected_group
        assert 'extras' not in group_list[0]
        assert 'tags' not in group_list[0]
        assert 'groups' not in group_list[0]
        assert 'users' not in group_list[0]
        assert 'datasets' not in group_list[0]

    def _create_bulk_groups(self, name, count):
        from ckan import model
        model.repo.new_revision()
        groups = [model.Group(name='{}_{}'.format(name, i))
                  for i in range(count)]
        model.Session.add_all(groups)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_groups('group_default', 1010)
        results = helpers.call_action('group_list')
        eq(len(results), 1000)  # i.e. default value

    @helpers.change_config('ckan.group_and_organization_list_max', '5')
    def test_limit_configured(self):
        self._create_bulk_groups('group_default', 7)
        results = helpers.call_action('group_list')
        eq(len(results), 5)  # i.e. configured limit

    def test_all_fields_limit_default(self):
        self._create_bulk_groups('org_all_fields_default', 30)
        results = helpers.call_action('group_list', all_fields=True)
        eq(len(results), 25)  # i.e. default value

    @helpers.change_config('ckan.group_and_organization_list_all_fields_max', '5')
    def test_all_fields_limit_configured(self):
        self._create_bulk_groups('org_all_fields_default', 30)
        results = helpers.call_action('group_list', all_fields=True)
        eq(len(results), 5)  # i.e. configured limit

    def test_group_list_extras_returned(self):

        group = factories.Group(extras=[{'key': 'key1', 'value': 'val1'}])

        group_list = helpers.call_action('group_list', all_fields=True,
                                         include_extras=True)

        eq(group_list[0]['extras'], group['extras'])
        eq(group_list[0]['extras'][0]['key'], 'key1')

    def test_group_list_users_returned(self):
        user = factories.User()
        group = factories.Group(users=[{'name': user['name'],
                                        'capacity': 'admin'}])

        group_list = helpers.call_action('group_list', all_fields=True,
                                         include_users=True)

        eq(group_list[0]['users'], group['users'])
        eq(group_list[0]['users'][0]['name'], group['users'][0]['name'])

    # NB there is no test_group_list_tags_returned because tags are not in the
    # group_create schema (yet)

    def test_group_list_groups_returned(self):

        parent_group = factories.Group(tags=[{'name': 'river'}])
        child_group = factories.Group(groups=[{'name': parent_group['name']}],
                                      tags=[{'name': 'river'}])

        group_list = helpers.call_action('group_list', all_fields=True,
                                         include_groups=True)

        child_group_returned = group_list[0]
        if group_list[0]['name'] == child_group['name']:
            child_group_returned, parent_group_returned = group_list
        else:
            child_group_returned, parent_group_returned = group_list[::-1]
        expected_parent_group = dict(parent_group.items()[:])

        eq([g['name'] for g in child_group_returned['groups']], [expected_parent_group['name']])

    def test_group_list_limit(self):

        group1 = factories.Group()
        group2 = factories.Group()
        group3 = factories.Group()

        group_list = helpers.call_action('group_list', limit=1)

        eq(len(group_list), 1)
        eq(group_list[0], group1['name'])

    def test_group_list_offset(self):

        group1 = factories.Group()
        group2 = factories.Group()
        group3 = factories.Group()

        group_list = helpers.call_action('group_list', offset=2)

        eq(len(group_list), 1)
        eq(group_list[0], group3['name'])

    def test_group_list_limit_and_offset(self):

        group1 = factories.Group()
        group2 = factories.Group()
        group3 = factories.Group()

        group_list = helpers.call_action('group_list', offset=1, limit=1)

        eq(len(group_list), 1)
        eq(group_list[0], group2['name'])

    def test_group_list_wrong_limit(self):

        assert_raises(logic.ValidationError, helpers.call_action, 'group_list',
                      limit='a')

    def test_group_list_wrong_offset(self):

        assert_raises(logic.ValidationError, helpers.call_action, 'group_list',
                      offset='-2')


class TestGroupShow(helpers.FunctionalTestBase):

    def test_group_show(self):
        group = factories.Group(user=factories.User())

        group_dict = helpers.call_action('group_show', id=group['id'],
                                         include_datasets=True)

        group_dict.pop('packages', None)
        eq(group_dict, group)

    def test_group_show_error_not_found(self):

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'group_show', id='does_not_exist')

    def test_group_show_error_for_organization(self):

        org = factories.Organization()

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'group_show', id=org['id'])

    def test_group_show_packages_returned(self):

        user_name = helpers.call_action('get_site_user')['name']

        group = factories.Group(user=factories.User())

        datasets = [
            {'name': 'dataset_1', 'groups': [{'name': group['name']}]},
            {'name': 'dataset_2', 'groups': [{'name': group['name']}]},
        ]

        for dataset in datasets:
            helpers.call_action('package_create',
                                context={'user': user_name},
                                **dataset)

        group_dict = helpers.call_action('group_show', id=group['id'],
                                         include_datasets=True)

        assert len(group_dict['packages']) == 2
        assert group_dict['package_count'] == 2

    def test_group_show_packages_returned_for_view(self):

        user_name = helpers.call_action('get_site_user')['name']

        group = factories.Group(user=factories.User())

        datasets = [
            {'name': 'dataset_1', 'groups': [{'name': group['name']}]},
            {'name': 'dataset_2', 'groups': [{'name': group['name']}]},
        ]

        for dataset in datasets:
            helpers.call_action('package_create',
                                context={'user': user_name},
                                **dataset)

        group_dict = helpers.call_action('group_show', id=group['id'],
                                         include_datasets=True,
                                         context={'for_view': True})

        assert len(group_dict['packages']) == 2
        assert group_dict['package_count'] == 2

    def test_group_show_no_packages_returned(self):

        user_name = helpers.call_action('get_site_user')['name']

        group = factories.Group(user=factories.User())

        datasets = [
            {'name': 'dataset_1', 'groups': [{'name': group['name']}]},
            {'name': 'dataset_2', 'groups': [{'name': group['name']}]},
        ]

        for dataset in datasets:
            helpers.call_action('package_create',
                                context={'user': user_name},
                                **dataset)

        group_dict = helpers.call_action('group_show', id=group['id'],
                                         include_datasets=False)

        assert 'packages' not in group_dict
        assert group_dict['package_count'] == 2

    def test_group_show_does_not_show_private_datasets(self):
        '''group_show() should never show private datasets.

        If a dataset is a private member of an organization and also happens to
        be a member of a group, group_show() should not return the dataset as
        part of the group dict, even if the user calling group_show() is a
        member or admin of the group or the organization or is a sysadmin.

        '''
        org_member = factories.User()
        org = factories.Organization(user=org_member)
        private_dataset = factories.Dataset(user=org_member,
                                            owner_org=org['name'], private=True)

        group = factories.Group()

        # Add the private dataset to the group.
        helpers.call_action('member_create', id=group['id'],
                            object=private_dataset['id'], object_type='package',
                            capacity='public')

        # Create a member user and an admin user of the group.
        group_member = factories.User()
        helpers.call_action('member_create', id=group['id'],
                            object=group_member['id'], object_type='user',
                            capacity='member')
        group_admin = factories.User()
        helpers.call_action('member_create', id=group['id'],
                            object=group_admin['id'], object_type='user',
                            capacity='admin')

        # Create a user who isn't a member of any group or organization.
        non_member = factories.User()

        sysadmin = factories.Sysadmin()

        # None of the users should see the dataset when they call group_show().
        for user in (org_member, group_member, group_admin, non_member,
                     sysadmin, None):

            if user is None:
                context = None  # No user logged-in.
            else:
                context = {'user': user['name']}

            group = helpers.call_action('group_show', id=group['id'],
                                        include_datasets=True, context=context)

            assert private_dataset['id'] not in [dataset['id'] for dataset
                                                 in group['packages']], (
                "group_show() should never show private datasets")

    @helpers.change_config('ckan.search.rows_max', '5')
    def test_package_limit_configured(self):
        group = factories.Group()
        for i in range(7):
            factories.Dataset(groups=[{'id': group['id']}])
        id = group['id']

        results = helpers.call_action('group_show', id=id,
                                      include_datasets=1)
        eq(len(results['packages']), 5)  # i.e. ckan.search.rows_max


class TestOrganizationList(helpers.FunctionalTestBase):

    def test_organization_list(self):

        org1 = factories.Organization()
        org2 = factories.Organization()

        org_list = helpers.call_action('organization_list')

        assert (sorted(org_list) ==
                sorted([g['name'] for g in [org1, org2]]))

    def test_organization_list_in_presence_of_groups(self):
        '''
        Getting the organization_list only returns organization group
        types.
        '''
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group()
        factories.Group()

        org_list = helpers.call_action('organization_list')

        assert (sorted(org_list) ==
                sorted([g['name'] for g in [org1, org2]]))

    def test_organization_list_in_presence_of_custom_group_types(self):
        '''
        Getting the organization_list only returns organization group
        types.
        '''
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action('organization_list')

        assert (sorted(org_list) ==
                sorted([g['name'] for g in [org1, org2]]))

    def test_organization_list_return_custom_organization_type(self):
        '''
        Getting the org_list with a type defined should only return
        orgs of that type.
        '''
        org1 = factories.Organization()
        org2 = factories.Organization(type="custom_org")
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action('organization_list', type='custom_org')

        assert (sorted(org_list) ==
                sorted([g['name'] for g in [org2]])), '{}'.format(org_list)

    def _create_bulk_orgs(self, name, count):
        from ckan import model
        model.repo.new_revision()
        orgs = [model.Group(name='{}_{}'.format(name, i), is_organization=True,
                            type='organization')
                for i in range(count)]
        model.Session.add_all(orgs)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_orgs('org_default', 1010)
        results = helpers.call_action('organization_list')
        eq(len(results), 1000)  # i.e. default value

    @helpers.change_config('ckan.group_and_organization_list_max', '5')
    def test_limit_configured(self):
        self._create_bulk_orgs('org_default', 7)
        results = helpers.call_action('organization_list')
        eq(len(results), 5)  # i.e. configured limit

    def test_all_fields_limit_default(self):
        self._create_bulk_orgs('org_all_fields_default', 30)
        results = helpers.call_action('organization_list', all_fields=True)
        eq(len(results), 25)  # i.e. default value

    @helpers.change_config('ckan.group_and_organization_list_all_fields_max', '5')
    def test_all_fields_limit_configured(self):
        self._create_bulk_orgs('org_all_fields_default', 30)
        results = helpers.call_action('organization_list', all_fields=True)
        eq(len(results), 5)  # i.e. configured limit


class TestOrganizationShow(helpers.FunctionalTestBase):

    def test_organization_show(self):
        org = factories.Organization()

        org_dict = helpers.call_action('organization_show', id=org['id'],
                                       include_datasets=True)

        org_dict.pop('packages', None)
        eq(org_dict, org)

    def test_organization_show_error_not_found(self):

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'organization_show', id='does_not_exist')

    def test_organization_show_error_for_group(self):

        group = factories.Group()

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'organization_show', id=group['id'])

    def test_organization_show_packages_returned(self):

        user_name = helpers.call_action('get_site_user')['name']

        org = factories.Organization()

        datasets = [
            {'name': 'dataset_1', 'owner_org': org['name']},
            {'name': 'dataset_2', 'owner_org': org['name']},
        ]

        for dataset in datasets:
            helpers.call_action('package_create',
                                context={'user': user_name},
                                **dataset)

        org_dict = helpers.call_action('organization_show', id=org['id'],
                                       include_datasets=True)

        assert len(org_dict['packages']) == 2
        assert org_dict['package_count'] == 2

    def test_organization_show_private_packages_not_returned(self):

        user_name = helpers.call_action('get_site_user')['name']

        org = factories.Organization()

        datasets = [
            {'name': 'dataset_1', 'owner_org': org['name']},
            {'name': 'dataset_2', 'owner_org': org['name'], 'private': True},
        ]

        for dataset in datasets:
            helpers.call_action('package_create',
                                context={'user': user_name},
                                **dataset)

        org_dict = helpers.call_action('organization_show', id=org['id'],
                                       include_datasets=True)

        assert len(org_dict['packages']) == 1
        assert org_dict['packages'][0]['name'] == 'dataset_1'
        assert org_dict['package_count'] == 1

    @helpers.change_config('ckan.search.rows_max', '5')
    def test_package_limit_configured(self):
        org = factories.Organization()
        for i in range(7):
            factories.Dataset(owner_org=org['id'])
        id = org['id']

        results = helpers.call_action('organization_show', id=id,
                                      include_datasets=1)
        eq(len(results['packages']), 5)  # i.e. ckan.search.rows_max


class TestUserList(helpers.FunctionalTestBase):

    def test_user_list_default_values(self):

        user = factories.User()

        got_users = helpers.call_action('user_list')

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user['id'] == user['id']
        assert got_user['name'] == user['name']
        assert got_user['fullname'] == user['fullname']
        assert got_user['display_name'] == user['display_name']
        assert got_user['created'] == user['created']
        assert got_user['about'] == user['about']
        assert got_user['sysadmin'] == user['sysadmin']
        assert got_user['number_of_edits'] == 0
        assert got_user['number_created_packages'] == 0
        assert 'password' not in got_user
        assert 'reset_key' not in got_user
        assert 'apikey' not in got_user
        assert 'email' not in got_user
        assert 'datasets' not in got_user

    def test_user_list_edits(self):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        dataset['title'] = 'Edited title'
        helpers.call_action('package_update',
                            context={'user': user['name']},
                            **dataset)

        got_users = helpers.call_action('user_list')

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user['number_created_packages'] == 1
        assert got_user['number_of_edits'] == 2

    def test_user_list_excludes_deleted_users(self):

        user = factories.User()
        factories.User(state='deleted')

        got_users = helpers.call_action('user_list')

        assert len(got_users) == 1
        assert got_users[0]['name'] == user['name']

    def test_user_list_not_all_fields(self):

        user = factories.User()

        got_users = helpers.call_action('user_list', all_fields=False)

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user == user['name']

    def test_user_list_filtered_by_email(self):

        user_a = factories.User(email='a@example.com')
        factories.User(email='b@example.com')

        got_users = helpers.call_action('user_list', email='a@example.com',
                                        all_fields=False)

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user == user_a['name']


class TestUserShow(helpers.FunctionalTestBase):

    def test_user_show_default_values(self):

        user = factories.User()

        got_user = helpers.call_action('user_show', id=user['id'])

        assert got_user['id'] == user['id']
        assert got_user['name'] == user['name']
        assert got_user['fullname'] == user['fullname']
        assert got_user['display_name'] == user['display_name']
        assert got_user['created'] == user['created']
        assert got_user['about'] == user['about']
        assert got_user['sysadmin'] == user['sysadmin']
        assert got_user['number_of_edits'] == 0
        assert got_user['number_created_packages'] == 0
        assert 'password' not in got_user
        assert 'reset_key' not in got_user
        assert 'apikey' not in got_user
        assert 'email' not in got_user
        assert 'datasets' not in got_user
        assert 'password_hash' not in got_user

    def test_user_show_keep_email(self):

        user = factories.User()

        got_user = helpers.call_action('user_show',
                                       context={'keep_email': True},
                                       id=user['id'])

        assert got_user['email'] == user['email']
        assert 'apikey' not in got_user
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

    def test_user_show_keep_apikey(self):

        user = factories.User()

        got_user = helpers.call_action('user_show',
                                       context={'keep_apikey': True},
                                       id=user['id'])

        assert 'email' not in got_user
        assert got_user['apikey'] == user['apikey']
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

    def test_user_show_normal_user_no_password_hash(self):

        user = factories.User()

        got_user = helpers.call_action('user_show',
                                       id=user['id'],
                                       include_password_hash=True)

        assert 'password_hash' not in got_user

    def test_user_show_for_myself(self):

        user = factories.User()

        got_user = helpers.call_action('user_show',
                                       context={'user': user['name']},
                                       id=user['id'])

        assert got_user['email'] == user['email']
        assert got_user['apikey'] == user['apikey']
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

    def test_user_show_sysadmin_values(self):

        user = factories.User()

        sysadmin = factories.User(sysadmin=True)

        got_user = helpers.call_action('user_show',
                                       context={'user': sysadmin['name']},
                                       id=user['id'])

        assert got_user['email'] == user['email']
        assert got_user['apikey'] == user['apikey']
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

    def test_user_show_sysadmin_password_hash(self):

        user = factories.User(password='TestPassword1')

        sysadmin = factories.User(sysadmin=True)

        got_user = helpers.call_action('user_show',
                                       context={'user': sysadmin['name']},
                                       id=user['id'],
                                       include_password_hash=True)

        assert got_user['email'] == user['email']
        assert got_user['apikey'] == user['apikey']
        assert 'password_hash' in got_user
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

    def test_user_show_include_datasets(self):

        user = factories.User()
        dataset = factories.Dataset(user=user)

        got_user = helpers.call_action('user_show',
                                       include_datasets=True,
                                       id=user['id'])

        assert len(got_user['datasets']) == 1
        assert got_user['datasets'][0]['name'] == dataset['name']

    def test_user_show_include_datasets_excludes_draft_and_private(self):

        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        got_user = helpers.call_action('user_show',
                                       include_datasets=True,
                                       id=user['id'])

        assert len(got_user['datasets']) == 1
        assert got_user['datasets'][0]['name'] == dataset['name']
        assert got_user['number_created_packages'] == 1

    def test_user_show_include_datasets_includes_draft_myself(self):
        # a user viewing his own user should see the draft and private datasets

        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        dataset_deleted = factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        got_user = helpers.call_action('user_show',
                                       context={'user': user['name']},
                                       include_datasets=True,
                                       id=user['id'])

        eq(len(got_user['datasets']), 3)
        datasets_got = set([user_['name'] for user_ in got_user['datasets']])
        assert dataset_deleted['name'] not in datasets_got
        eq(got_user['number_created_packages'], 3)

    def test_user_show_include_datasets_includes_draft_sysadmin(self):
        # sysadmin should see the draft and private datasets

        user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        dataset_deleted = factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        got_user = helpers.call_action('user_show',
                                       context={'user': sysadmin['name']},
                                       include_datasets=True,
                                       id=user['id'])

        eq(len(got_user['datasets']), 3)
        datasets_got = set([user_['name'] for user_ in got_user['datasets']])
        assert dataset_deleted['name'] not in datasets_got
        eq(got_user['number_created_packages'], 3)


class TestCurrentPackageList(helpers.FunctionalTestBase):

    def test_current_package_list(self):
        '''
        Test current_package_list_with_resources with no parameters
        '''
        user = factories.User()
        dataset1 = factories.Dataset(user=user)
        dataset2 = factories.Dataset(user=user)
        current_package_list = helpers. \
            call_action('current_package_list_with_resources')
        eq(len(current_package_list), 2)

    def test_current_package_list_limit_param(self):
        '''
        Test current_package_list_with_resources with limit parameter
        '''
        user = factories.User()
        dataset1 = factories.Dataset(user=user)
        dataset2 = factories.Dataset(user=user)
        current_package_list = helpers. \
            call_action('current_package_list_with_resources', limit=1)
        eq(len(current_package_list), 1)
        eq(current_package_list[0]['name'], dataset2['name'])

    def test_current_package_list_offset_param(self):
        '''
        Test current_package_list_with_resources with offset parameter
        '''
        user = factories.User()
        dataset1 = factories.Dataset(user=user)
        dataset2 = factories.Dataset(user=user)
        current_package_list = helpers. \
            call_action('current_package_list_with_resources', offset=1)
        eq(len(current_package_list), 1)
        eq(current_package_list[0]['name'], dataset1['name'])

    def test_current_package_list_private_datasets_anonoymous_user(self):
        '''
        Test current_package_list_with_resources with an anoymous user and
        a private dataset
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset1 = factories.Dataset(user=user, owner_org=org['name'],
                                     private=True)
        dataset2 = factories.Dataset(user=user)
        current_package_list = helpers. \
            call_action('current_package_list_with_resources', context={})
        eq(len(current_package_list), 1)

    def test_current_package_list_private_datasets_sysadmin_user(self):
        '''
        Test current_package_list_with_resources with a sysadmin user and a
        private dataset
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset1 = factories.Dataset(user=user, owner_org=org['name'],
                                     private=True)
        dataset2 = factories.Dataset(user=user)
        sysadmin = factories.Sysadmin()
        current_package_list = helpers. \
            call_action('current_package_list_with_resources', context={'user':
                        sysadmin['name']})
        eq(len(current_package_list), 2)


class TestPackageAutocomplete(helpers.FunctionalTestBase):

    def test_package_autocomplete_does_not_return_private_datasets(self):

        user = factories.User()
        org = factories.Organization(user=user)
        dataset1 = factories.Dataset(user=user, owner_org=org['name'],
                                     title='Some public stuff')
        dataset2 = factories.Dataset(user=user, owner_org=org['name'],
                                     private=True, title='Some private stuff')

        package_list = helpers.call_action(
            'package_autocomplete', context={'ignore_auth': False}, q='some'
        )
        eq(len(package_list), 1)

    def test_package_autocomplete_does_return_private_datasets_from_my_org(self):
        user = factories.User()
        org = factories.Organization(
            users=[{'name': user['name'], 'capacity': 'member'}]
        )
        factories.Dataset(
            user=user, owner_org=org['id'], title='Some public stuff'
        )
        factories.Dataset(
            user=user, owner_org=org['id'], private=True,
            title='Some private stuff'
        )
        package_list = helpers.call_action(
            'package_autocomplete',
            context={'user': user['name'], 'ignore_auth': False},
            q='some'
        )
        eq(len(package_list), 2)

    def test_package_autocomplete_works_for_the_middle_part_of_title(self):
        factories.Dataset(title='Some public stuff')
        factories.Dataset(title='Some random stuff')

        package_list = helpers.call_action('package_autocomplete', q='bli')
        eq(len(package_list), 1)
        package_list = helpers.call_action('package_autocomplete', q='tuf')
        eq(len(package_list), 2)


class TestPackageSearch(helpers.FunctionalTestBase):

    def test_search(self):
        factories.Dataset(title='Rivers')
        factories.Dataset(title='Lakes')  # decoy

        search_result = helpers.call_action('package_search', q='rivers')

        eq(search_result['results'][0]['title'], 'Rivers')
        eq(search_result['count'], 1)

    def test_search_fl(self):
        d1 = factories.Dataset(title='Rivers', name='test_ri')
        d2 = factories.Dataset(title='Lakes')

        search_result = helpers.call_action('package_search', q='rivers', fl=['title', 'name'])
        eq(search_result['results'], [{'title': 'Rivers', 'name': 'test_ri'}])

        search_result = helpers.call_action('package_search', q='rivers', fl='title,name')
        eq(search_result['results'], [{'title': 'Rivers', 'name': 'test_ri'}])

        search_result = helpers.call_action('package_search', q='rivers', fl=['id'])
        eq(search_result['results'], [{'id': d1['id']}])

    def test_search_all(self):
        factories.Dataset(title='Rivers')
        factories.Dataset(title='Lakes')

        search_result = helpers.call_action('package_search')  # no q

        eq(search_result['count'], 2)

    def test_bad_action_parameter(self):
        nose.tools.assert_raises(
            SearchError,
            helpers.call_action,
            'package_search', weird_param=1)

    def test_bad_solr_parameter(self):
        nose.tools.assert_raises(
            SearchError,
            helpers.call_action,
            'package_search', sort='metadata_modified')
        # SOLR doesn't like that we didn't specify 'asc' or 'desc'
        # SOLR error is 'Missing sort order' or 'Missing_sort_order',
        # depending on the solr version.

    def _create_bulk_datasets(self, name, count):
        from ckan import model
        model.repo.new_revision()
        pkgs = [model.Package(name='{}_{}'.format(name, i))
                for i in range(count)]
        model.Session.add_all(pkgs)
        model.repo.commit_and_remove()

    def test_rows_returned_default(self):
        self._create_bulk_datasets('rows_default', 11)
        results = logic.get_action('package_search')({}, {})
        eq(len(results['results']), 10)  # i.e. 'rows' default value

    @helpers.change_config('ckan.search.rows_max', '12')
    def test_rows_returned_limited(self):
        self._create_bulk_datasets('rows_limited', 14)
        results = logic.get_action('package_search')({}, {'rows': '15'})
        eq(len(results['results']), 12)  # i.e. ckan.search.rows_max

    def test_facets(self):
        org = factories.Organization(name='test-org-facet', title='Test Org')
        factories.Dataset(owner_org=org['id'])
        factories.Dataset(owner_org=org['id'])

        data_dict = {'facet.field': ['organization']}
        search_result = helpers.call_action('package_search', **data_dict)

        eq(search_result['count'], 2)
        eq(search_result['search_facets'],
           {'organization': {'items': [{'count': 2,
                                        'display_name': u'Test Org',
                                        'name': 'test-org-facet'}],
                             'title': 'organization'}})

    def test_facet_limit(self):
        group1 = factories.Group(name='test-group-fl1', title='Test Group 1')
        group2 = factories.Group(name='test-group-fl2', title='Test Group 2')
        factories.Dataset(groups=[{'name': group1['name']},
                                  {'name': group2['name']}])
        factories.Dataset(groups=[{'name': group1['name']}])
        factories.Dataset()

        data_dict = {'facet.field': ['groups'],
                     'facet.limit': 1}
        search_result = helpers.call_action('package_search', **data_dict)

        eq(len(search_result['search_facets']['groups']['items']), 1)
        eq(search_result['search_facets'],
           {'groups': {'items': [{'count': 2,
                                  'display_name': u'Test Group 1',
                                  'name': 'test-group-fl1'}],
                       'title': 'groups'}})

    def test_facet_no_limit(self):
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Dataset(groups=[{'name': group1['name']},
                                  {'name': group2['name']}])
        factories.Dataset(groups=[{'name': group1['name']}])
        factories.Dataset()

        data_dict = {'facet.field': ['groups'],
                     'facet.limit': -1}  # no limit
        search_result = helpers.call_action('package_search', **data_dict)

        eq(len(search_result['search_facets']['groups']['items']), 2)

    def test_sort(self):
        factories.Dataset(name='test0')
        factories.Dataset(name='test1')
        factories.Dataset(name='test2')

        search_result = helpers.call_action('package_search',
                                            sort='metadata_created desc')

        result_names = [result['name'] for result in search_result['results']]
        eq(result_names, [u'test2', u'test1', u'test0'])

    def test_package_search_on_resource_name(self):
        '''
        package_search() should allow searching on resource name field.
        '''
        resource_name = 'resource_abc'
        factories.Resource(name=resource_name)

        search_result = helpers.call_action('package_search', q='resource_abc')
        eq(search_result['results'][0]['resources'][0]['name'], resource_name)

    def test_package_search_excludes_private_and_drafts(self):
        '''
        package_search() with no options should not return private and draft
        datasets.
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = helpers.call_action('package_search')['results']

        eq(len(results), 1)
        eq(results[0]['name'], dataset['name'])

    def test_package_search_with_fq_excludes_private(self):
        '''
        package_search() with fq capacity:private should not return private
        and draft datasets.
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        fq = "capacity:private"
        results = helpers.call_action('package_search', fq=fq)['results']

        eq(len(results), 0)

    def test_package_search_with_fq_excludes_drafts(self):
        '''
        A sysadmin user can't use fq drafts to get draft datasets. Nothing is
        returned.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        factories.Dataset(user=user, state='draft', name="draft-dataset")
        factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "state:draft"
        results = helpers.call_action('package_search', fq=fq)['results']

        eq(len(results), 0)

    def test_package_search_with_include_drafts_option_excludes_drafts_for_anon_user(self):
        '''
        An anon user can't user include_drafts to get draft datasets.
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        draft_dataset = factories.Dataset(user=user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = logic.get_action('package_search')(
            {u'user': u''}, {'include_drafts': True})['results']

        eq(len(results), 1)
        nose.tools.assert_not_equals(results[0]['name'], draft_dataset['name'])
        nose.tools.assert_equal(results[0]['name'], dataset['name'])

    def test_package_search_with_include_drafts_option_includes_drafts_for_sysadmin(self):
        '''
        A sysadmin can use the include_drafts option to get draft datasets for
        all users.
        '''
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        draft_dataset = factories.Dataset(user=user, state='draft')
        other_draft_dataset = factories.Dataset(user=other_user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = logic.get_action('package_search')(
            {'user': sysadmin['name']}, {'include_drafts': True})['results']

        eq(len(results), 3)
        names = [r['name'] for r in results]
        nose.tools.assert_true(draft_dataset['name'] in names)
        nose.tools.assert_true(other_draft_dataset['name'] in names)
        nose.tools.assert_true(dataset['name'] in names)

    def test_package_search_with_include_drafts_false_option_doesnot_include_drafts_for_sysadmin(self):
        '''
        A sysadmin with include_drafts option set to `False` will not get
        drafts returned in results.
        '''
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state='deleted')
        draft_dataset = factories.Dataset(user=user, state='draft')
        other_draft_dataset = factories.Dataset(user=other_user, state='draft')
        factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = logic.get_action('package_search')(
            {'user': sysadmin['name']}, {'include_drafts': False})['results']

        eq(len(results), 1)
        names = [r['name'] for r in results]
        nose.tools.assert_true(draft_dataset['name'] not in names)
        nose.tools.assert_true(other_draft_dataset['name'] not in names)
        nose.tools.assert_true(dataset['name'] in names)

    def test_package_search_with_include_drafts_option_includes_drafts_for_user(self):
        '''
        The include_drafts option will include draft datasets for the
        authorized user, but not drafts for other users.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        draft_dataset = factories.Dataset(user=user, state='draft', name="draft-dataset")
        other_draft_dataset = factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        results = logic.get_action('package_search')(
            {'user': user['name']}, {'include_drafts': True})['results']

        eq(len(results), 3)
        names = [r['name'] for r in results]
        nose.tools.assert_true(draft_dataset['name'] in names)
        nose.tools.assert_true(other_draft_dataset['name'] not in names)
        nose.tools.assert_true(dataset['name'] in names)
        nose.tools.assert_true(other_dataset['name'] in names)

    def test_package_search_with_fq_for_create_user_id_will_include_datasets_for_other_users(self):
        '''
        A normal user can use the fq creator_user_id to get active datasets
        (but not draft) for another user.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        draft_dataset = factories.Dataset(user=user, state='draft', name="draft-dataset")
        other_draft_dataset = factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "creator_user_id:{0}".format(other_user['id'])
        results = logic.get_action('package_search')(
            {'user': user['name']}, {'fq': fq})['results']

        eq(len(results), 1)
        names = [r['name'] for r in results]
        nose.tools.assert_true(draft_dataset['name'] not in names)
        nose.tools.assert_true(other_draft_dataset['name'] not in names)
        nose.tools.assert_true(dataset['name'] not in names)
        nose.tools.assert_true(other_dataset['name'] in names)

    def test_package_search_with_fq_for_create_user_id_will_not_include_drafts_for_other_users(self):
        '''
        A normal user can't use fq creator_user_id and drafts to get draft
        datasets for another user.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        factories.Dataset(user=user, state='draft', name="draft-dataset")
        factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user['id'])
        results = logic.get_action('package_search')(
            {'user': user['name']},
            {'fq': fq, 'include_drafts': True})['results']

        eq(len(results), 0)

    def test_package_search_with_fq_for_creator_user_id_and_drafts_and_include_drafts_option_will_not_include_drafts_for_other_user(self):
        '''
        A normal user can't use fq creator_user_id and drafts and the
        include_drafts option to get draft datasets for another user.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        factories.Dataset(user=user, state='draft', name="draft-dataset")
        factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user['id'])
        results = logic.get_action('package_search')(
            {'user': user['name']},
            {'fq': fq, 'include_drafts': True})['results']

        eq(len(results), 0)

    def test_package_search_with_fq_for_creator_user_id_and_include_drafts_option_will_not_include_drafts_for_other_user(self):
        '''
        A normal user can't use fq creator_user_id and the include_drafts
        option to get draft datasets for another user.
        '''
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        factories.Dataset(user=user, state='draft', name="draft-dataset")
        other_draft_dataset = factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "creator_user_id:{0}".format(other_user['id'])
        results = logic.get_action('package_search')(
            {'user': user['name']},
            {'fq': fq, 'include_drafts': True})['results']

        names = [r['name'] for r in results]
        eq(len(results), 1)
        nose.tools.assert_true(other_dataset['name'] in names)
        nose.tools.assert_true(other_draft_dataset['name'] not in names)

    def test_package_search_with_fq_for_create_user_id_will_include_drafts_for_other_users_for_sysadmin(self):
        '''
        Sysadmins can use fq to get draft datasets for another user.
        '''
        user = factories.User()
        sysadmin = factories.Sysadmin()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state='deleted', name="deleted-dataset")
        draft_dataset = factories.Dataset(user=user, state='draft', name="draft-dataset")
        factories.Dataset(user=other_user, state='draft', name="other-draft-dataset")
        factories.Dataset(user=user, private=True, owner_org=org['name'], name="private-dataset")

        fq = "(creator_user_id:{0} AND +state:draft)".format(user['id'])
        results = logic.get_action('package_search')(
            {'user': sysadmin['name']},
            {'fq': fq})['results']

        names = [r['name'] for r in results]
        eq(len(results), 1)
        nose.tools.assert_true(dataset['name'] not in names)
        nose.tools.assert_true(draft_dataset['name'] in names)

    def test_package_search_private_with_include_private(self):
        '''
        package_search() can return private datasets when
        `include_private=True`
        '''
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, state='deleted')
        factories.Dataset(user=user, state='draft')
        private_dataset = factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = logic.get_action('package_search')(
            {'user': user['name']}, {'include_private': True})['results']

        eq([r['name'] for r in results], [private_dataset['name']])

    def test_package_search_private_with_include_private_wont_show_other_orgs_private(self):
        user = factories.User()
        user2 = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user2)
        private_dataset = factories.Dataset(user=user2, private=True, owner_org=org2['name'])

        results = logic.get_action('package_search')(
            {'user': user['name']}, {'include_private': True})['results']

        eq([r['name'] for r in results], [])

    def test_package_search_private_with_include_private_syadmin(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        private_dataset = factories.Dataset(user=user, private=True, owner_org=org['name'])

        results = logic.get_action('package_search')(
            {'user': sysadmin['name']}, {'include_private': True})['results']

        eq([r['name'] for r in results], [private_dataset['name']])

    def test_package_works_without_user_in_context(self):
        '''
        package_search() should work even if user isn't in the context (e.g.
        ckanext-showcase tests.
        '''
        logic.get_action('package_search')({}, dict(q='anything'))

    def test_local_parameters_not_supported(self):
        nose.tools.assert_raises(
            SearchError,
            helpers.call_action,
            'package_search',
            q='{!child of="content_type:parentDoc"}')


class TestPackageAutocompleteWithDatasetForm(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckan.plugins'] = 'example_idatasetform'

    @classmethod
    def teardown_class(cls):
        super(TestPackageAutocompleteWithDatasetForm, cls).teardown_class()
        if p.plugin_loaded('example_idatasetform'):
            p.unload('example_idatasetform')

    def test_custom_schema_returned(self):
        dataset1 = factories.Dataset(custom_text='foo')

        query = helpers.call_action('package_search',
                                    q='id:{0}'.format(dataset1['id']))

        eq(query['results'][0]['id'], dataset1['id'])
        eq(query['results'][0]['custom_text'], 'foo')

    def test_custom_schema_not_returned(self):
        dataset1 = factories.Dataset(custom_text='foo')

        query = helpers.call_action('package_search',
                                    q='id:{0}'.format(dataset1['id']),
                                    use_default_schema=True)

        eq(query['results'][0]['id'], dataset1['id'])
        assert 'custom_text' not in query['results'][0]
        eq(query['results'][0]['extras'][0]['key'], 'custom_text')
        eq(query['results'][0]['extras'][0]['value'], 'foo')


class TestBadLimitQueryParameters(helpers.FunctionalTestBase):
    '''test class for #1258 non-int query parameters cause 500 errors

    Test that validation errors are raised when calling actions with
    bad parameters.
    '''

    def test_activity_list_actions(self):
        actions = [
            'user_activity_list',
            'package_activity_list',
            'group_activity_list',
            'organization_activity_list',
            'recently_changed_packages_activity_list',
            'current_package_list_with_resources',
        ]
        for action in actions:
            nose.tools.assert_raises(
                logic.ValidationError, helpers.call_action, action,
                id='test_user', limit='not_an_int', offset='not_an_int')
            nose.tools.assert_raises(
                logic.ValidationError, helpers.call_action, action,
                id='test_user', limit=-1, offset=-1)

    def test_package_search_facet_field_is_json(self):
        kwargs = {'facet.field': 'notjson'}
        nose.tools.assert_raises(
            logic.ValidationError, helpers.call_action, 'package_search',
            **kwargs)


class TestOrganizationListForUser(helpers.FunctionalTestBase):
    '''Functional tests for the organization_list_for_user() action function.'''

    def test_when_user_is_not_a_member_of_any_organizations(self):
        """
        When the user isn't a member of any organizations (in any capacity)
        organization_list_for_user() should return an empty list.
        """
        user = factories.User()
        context = {'user': user['name']}

        # Create an organization so we can test that it does not get returned.
        factories.Organization()

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert organizations == []

    def test_when_user_is_an_admin_of_one_organization(self):
        """
        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='admin')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert len(organizations) == 1
        assert organizations[0]['id'] == organization['id']

    def test_when_user_is_an_admin_of_three_organizations(self):
        """
        When the user is an admin of three organizations
        organization_list_for_user() should return a list of all three
        organizations.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization_1 = factories.Organization()
        organization_2 = factories.Organization()
        organization_3 = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        # Make the user an admin of all three organizations:
        for organization in (organization_1, organization_2, organization_3):
            helpers.call_action('member_create', id=organization['id'],
                                object=user['id'], object_type='user',
                                capacity='admin')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert len(organizations) == 3
        ids = [organization['id'] for organization in organizations]
        for organization in (organization_1, organization_2, organization_3):
            assert organization['id'] in ids

    def test_when_permissions_extend_to_sub_organizations(self):
        """

        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.

        """
        user = factories.User()
        context = {'user': user['name']}
        user['capacity'] = 'admin'
        top_organization = factories.Organization(users=[user])
        middle_organization = factories.Organization(users=[user])
        bottom_organization = factories.Organization()

        # Create another organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action('member_create',
                            id=bottom_organization['id'],
                            object=middle_organization['id'],
                            object_type='group', capacity='parent')
        helpers.call_action('member_create',
                            id=middle_organization['id'],
                            object=top_organization['id'],
                            object_type='group', capacity='parent')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert len(organizations) == 3
        org_ids = set(org['id'] for org in organizations)
        assert bottom_organization['id'] in org_ids

    def test_does_return_members(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just a member (not an admin) of.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='member')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert [org['id'] for org in organizations] == [organization['id']]

    def test_does_return_editors(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just an editor (not an admin) of.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='editor')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert [org['id'] for org in organizations] == [organization['id']]

    def test_editor_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is an editor of if passed a permission that belongs to the editor role.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='editor')

        organizations = helpers.call_action('organization_list_for_user',
                                            permission='create_dataset',
                                            context=context)

        assert [org['id'] for org in organizations] == [organization['id']]

    def test_member_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is a member of if passed a permission that belongs to the member role.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='member')

        organizations = helpers.call_action('organization_list_for_user',
                                            permission='read',
                                            context=context)

        assert [org['id'] for org in organizations] == [organization['id']]

    def test_invalid_permission(self):
        '''
        organization_list_for_user() should return an empty list if passed a
        non-existent or invalid permission.

        Note that we test this with a user who is an editor of one organization.
        If the user was an admin of the organization then it would return that
        organization - admins have all permissions, including permissions that
        don't exist.
        '''
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()
        factories.Organization()
        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='editor')

        for permission in ('', ' ', 'foo', 27.3, 5, True, False, None):
            organizations = helpers.call_action('organization_list_for_user',
                                                permission=permission,
                                                context=context)

        assert organizations == []

    def test_that_it_does_not_return_groups(self):
        """
        organization_list_for_user() should not return groups that the user is
        a member, editor or admin of.
        """
        user = factories.User()
        context = {'user': user['name']}
        group_1 = factories.Group()
        group_2 = factories.Group()
        group_3 = factories.Group()
        helpers.call_action('member_create', id=group_1['id'],
                            object=user['id'], object_type='user',
                            capacity='member')
        helpers.call_action('member_create', id=group_2['id'],
                            object=user['id'], object_type='user',
                            capacity='editor')
        helpers.call_action('member_create', id=group_3['id'],
                            object=user['id'], object_type='user',
                            capacity='admin')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert organizations == []

    def test_that_it_does_not_return_previous_memberships(self):
        """
        organization_list_for_user() should return organizations that the user
        was previously an admin of.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='admin')

        # Remove the user from the organization.
        helpers.call_action('member_delete', id=organization['id'],
                            object=user['id'], object_type='user')

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert organizations == []

    def test_when_user_is_sysadmin(self):
        """
        When the user is a sysadmin organization_list_for_user() should just
        return all organizations, even if the user is not a member of them.
        """
        user = factories.Sysadmin()
        context = {'user': user['name']}
        organization = factories.Organization()

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert [org['id'] for org in organizations] == [organization['id']]

    def test_that_it_does_not_return_deleted_organizations(self):
        """
        organization_list_for_user() should not return deleted organizations
        that the user was an admin of.
        """
        user = factories.User()
        context = {'user': user['name']}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action('member_create', id=organization['id'],
                            object=user['id'], object_type='user',
                            capacity='admin')

        # Delete the organization.
        helpers.call_action('organization_delete', id=organization['id'],
                            context=context)

        organizations = helpers.call_action('organization_list_for_user',
                                            context=context)

        assert organizations == []

    def test_with_no_authorized_user(self):
        """
        organization_list_for_user() should return an empty list if there's no
        authorized user. Users who aren't logged-in don't have any permissions.
        """
        # Create an organization so we can test that it doesn't get returned.
        organization = factories.Organization()

        organizations = helpers.call_action('organization_list_for_user')

        assert organizations == []

    def test_organization_list_for_user_returns_all_roles(self):

        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()

        org1 = factories.Organization(users=[
            {'name': user1['name'], 'capacity': 'admin'},
            {'name': user2['name'], 'capacity': 'editor'},
        ])
        org2 = factories.Organization(users=[
            {'name': user1['name'], 'capacity': 'member'},
            {'name': user2['name'], 'capacity': 'member'},
        ])
        org3 = factories.Organization(users=[
            {'name': user1['name'], 'capacity': 'editor'},
        ])

        org_list_for_user1 = helpers.call_action('organization_list_for_user',
                                                 id=user1['id'])

        assert sorted([org['id'] for org in org_list_for_user1]) == sorted([org1['id'], org2['id'], org3['id']])

        org_list_for_user2 = helpers.call_action('organization_list_for_user',
                                                 id=user2['id'])

        assert sorted([org['id'] for org in org_list_for_user2]) == sorted([org1['id'], org2['id']])

        org_list_for_user3 = helpers.call_action('organization_list_for_user',
                                                 id=user3['id'])

        eq(org_list_for_user3, [])


class TestShowResourceView(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def test_resource_view_show(self):

        resource = factories.Resource()
        resource_view = {'resource_id': resource['id'],
                         'view_type': u'image_view',
                         'title': u'View',
                         'description': u'A nice view',
                         'image_url': 'url'}

        new_view = helpers.call_action('resource_view_create', **resource_view)

        result = helpers.call_action('resource_view_show', id=new_view['id'])

        result.pop('id')
        result.pop('package_id')

        assert result == resource_view

    def test_resource_view_show_id_missing(self):

        nose.tools.assert_raises(
            logic.ValidationError,
            helpers.call_action, 'resource_view_show')

    def test_resource_view_show_id_not_found(self):

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'resource_view_show', id='does_not_exist')


class TestGetHelpShow(object):

    def test_help_show_basic(self):

        function_name = 'package_search'

        result = helpers.call_action('help_show', name=function_name)

        function = logic.get_action(function_name)

        eq(result, function.__doc__)

    def test_help_show_no_docstring(self):

        function_name = 'package_search'

        function = logic.get_action(function_name)

        actual_docstring = function.__doc__

        function.__doc__ = None

        result = helpers.call_action('help_show', name=function_name)

        function.__doc__ = actual_docstring

        eq(result, None)

    def test_help_show_not_found(self):

        function_name = 'unknown_action'

        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'help_show', name=function_name)


class TestConfigOptionShow(helpers.FunctionalTestBase):

    @helpers.change_config('ckan.site_title', 'My Test CKAN')
    def test_config_option_show_in_config_not_in_db(self):
        '''config_option_show returns value from config when value on in
        system_info table.'''

        title = helpers.call_action('config_option_show',
                                    key='ckan.site_title')
        nose.tools.assert_equal(title, 'My Test CKAN')

    @helpers.change_config('ckan.site_title', 'My Test CKAN')
    def test_config_option_show_in_config_and_in_db(self):
        '''config_option_show returns value from db when value is in both
        config and system_info table.'''

        params = {'ckan.site_title': 'Test site title'}
        helpers.call_action('config_option_update', **params)

        title = helpers.call_action('config_option_show',
                                    key='ckan.site_title')
        nose.tools.assert_equal(title, 'Test site title')

    @helpers.change_config('ckan.not.editable', 'My non editable option')
    def test_config_option_show_not_whitelisted_key(self):
        '''config_option_show raises exception if key is not a whitelisted
        config option.'''

        nose.tools.assert_raises(logic.ValidationError, helpers.call_action,
                                 'config_option_show', key='ckan.not.editable')


class TestConfigOptionList(object):

    def test_config_option_list(self):
        '''config_option_list returns whitelisted config option keys'''

        keys = helpers.call_action('config_option_list')
        schema_keys = schema.update_configuration_schema().keys()

        nose.tools.assert_equal(keys, schema_keys)


def remove_pseudo_users(user_list):
    pseudo_users = set(('logged_in', 'visitor'))
    user_list[:] = [user for user in user_list
                    if user['name'] not in pseudo_users]


class TestTagShow(helpers.FunctionalTestBase):

    def test_tag_show_for_free_tag(self):
        dataset = factories.Dataset(tags=[{'name': 'acid-rain'}])
        tag_in_dataset = dataset['tags'][0]

        tag_shown = helpers.call_action('tag_show', id='acid-rain')

        eq(tag_shown['name'], 'acid-rain')
        eq(tag_shown['display_name'], 'acid-rain')
        eq(tag_shown['id'], tag_in_dataset['id'])
        eq(tag_shown['vocabulary_id'], None)
        assert 'packages' not in tag_shown

    def test_tag_show_with_datasets(self):
        dataset = factories.Dataset(tags=[{'name': 'acid-rain'}])

        tag_shown = helpers.call_action('tag_show', id='acid-rain',
                                        include_datasets=True)

        eq([d['name'] for d in tag_shown['packages']], [dataset['name']])

    def test_tag_show_not_found(self):
        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'tag_show', id='does-not-exist')

    def test_tag_show_for_flexible_tag(self):
        # A 'flexible' tag is one with spaces, some punctuation
        # and foreign characters in its name
        dataset = factories.Dataset(tags=[{'name': u'Flexible. \u30a1'}])

        tag_shown = helpers.call_action('tag_show', id=u'Flexible. \u30a1',
                                        include_datasets=True)

        eq(tag_shown['name'], u'Flexible. \u30a1')
        eq(tag_shown['display_name'], u'Flexible. \u30a1')
        eq([d['name'] for d in tag_shown['packages']], [dataset['name']])

    def test_tag_show_for_vocab_tag(self):
        vocab = factories.Vocabulary(
            tags=[dict(name='acid-rain')])
        dataset = factories.Dataset(tags=vocab['tags'])
        tag_in_dataset = dataset['tags'][0]

        tag_shown = helpers.call_action('tag_show', id='acid-rain',
                                        vocabulary_id=vocab['id'],
                                        include_datasets=True)

        eq(tag_shown['name'], 'acid-rain')
        eq(tag_shown['display_name'], 'acid-rain')
        eq(tag_shown['id'], tag_in_dataset['id'])
        eq(tag_shown['vocabulary_id'], vocab['id'])
        eq([d['name'] for d in tag_shown['packages']], [dataset['name']])


class TestTagList(helpers.FunctionalTestBase):

    def test_tag_list(self):
        factories.Dataset(tags=[{'name': 'acid-rain'},
                                {'name': 'pollution'}])
        factories.Dataset(tags=[{'name': 'pollution'}])

        tag_list = helpers.call_action('tag_list')

        eq(set(tag_list), set(('acid-rain', 'pollution')))

    def test_tag_list_all_fields(self):
        factories.Dataset(tags=[{'name': 'acid-rain'}])

        tag_list = helpers.call_action('tag_list', all_fields=True)

        eq(tag_list[0]['name'], 'acid-rain')
        eq(tag_list[0]['display_name'], 'acid-rain')
        assert 'packages' not in tag_list

    def test_tag_list_with_flexible_tag(self):
        # A 'flexible' tag is one with spaces, punctuation (apart from commas)
        # and foreign characters in its name
        flexible_tag = u'Flexible. \u30a1'
        factories.Dataset(tags=[{'name': flexible_tag}])

        tag_list = helpers.call_action('tag_list', all_fields=True)

        eq(tag_list[0]['name'], flexible_tag)

    def test_tag_list_with_vocab(self):
        vocab = factories.Vocabulary(
            tags=[dict(name='acid-rain'),
                  dict(name='pollution')])

        tag_list = helpers.call_action('tag_list', vocabulary_id=vocab['id'])

        eq(set(tag_list), set(('acid-rain', 'pollution')))

    def test_tag_list_vocab_not_found(self):
        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action, 'tag_list', vocabulary_id='does-not-exist')


class TestRevisionList(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        super(TestRevisionList, cls).setup_class()
        helpers.reset_db()

    # Error cases

    def test_date_instead_of_revision(self):
        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action,
            'revision_list',
            since_id='2010-01-01T00:00:00')

    def test_date_invalid(self):
        nose.tools.assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'revision_list',
            since_time='2010-02-31T00:00:00')

    def test_revision_doesnt_exist(self):
        nose.tools.assert_raises(
            logic.NotFound,
            helpers.call_action,
            'revision_list',
            since_id='1234')

    def test_sort_param_not_valid(self):
        nose.tools.assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'revision_list',
            sort='invalid')

    # Normal usage

    @classmethod
    def _create_revisions(cls, num_revisions):
        from ckan import model
        rev_ids = []
        for i in xrange(num_revisions):
            rev = model.repo.new_revision()
            rev.id = text_type(i)
            model.Session.commit()
            rev_ids.append(rev.id)
        return rev_ids

    def test_all_revisions(self):
        rev_ids = self._create_revisions(2)
        revs = helpers.call_action('revision_list')
        # only test the 2 newest revisions, since the system creates one at
        # start-up.
        eq(revs[:2], rev_ids[::-1])

    def test_revisions_since_id(self):
        self._create_revisions(4)
        revs = helpers.call_action('revision_list', since_id='1')
        eq(revs, ['3', '2'])

    def test_revisions_since_time(self):
        from ckan import model
        self._create_revisions(4)

        rev1 = model.Session.query(model.Revision).get('1')
        revs = helpers.call_action('revision_list',
                                   since_time=rev1.timestamp.isoformat())
        eq(revs, ['3', '2'])

    def test_revisions_returned_are_limited(self):
        self._create_revisions(55)
        revs = helpers.call_action('revision_list', since_id='1')
        eq(len(revs), 50)  # i.e. limited to 50
        eq(revs[0], '54')
        eq(revs[-1], '5')

    def test_sort_asc(self):
        self._create_revisions(4)
        revs = helpers.call_action('revision_list', since_id='1',
                                   sort='time_asc')
        eq(revs, ['2', '3'])


class TestMembersList():

    def setup(self):
        helpers.reset_db()

    def test_dataset_delete_marks_membership_of_group_as_deleted(self):
        sysadmin = factories.Sysadmin()
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'name': group['name']}])
        context = {'user': sysadmin['name']}

        group_members = helpers.call_action('member_list', context,
                                            id=group['id'],
                                            object_type='package')

        eq(len(group_members), 1)
        eq(group_members[0][0], dataset['id'])
        eq(group_members[0][1], 'package')

        helpers.call_action('package_delete', context, id=dataset['id'])

        group_members = helpers.call_action('member_list', context,
                                            id=group['id'],
                                            object_type='package')

        eq(len(group_members), 0)

    def test_dataset_delete_marks_membership_of_org_as_deleted(self):
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'])
        context = {'user': sysadmin['name']}

        org_members = helpers.call_action('member_list', context,
                                          id=org['id'],
                                          object_type='package')

        eq(len(org_members), 1)
        eq(org_members[0][0], dataset['id'])
        eq(org_members[0][1], 'package')

        helpers.call_action('package_delete', context, id=dataset['id'])

        org_members = helpers.call_action('member_list', context,
                                          id=org['id'],
                                          object_type='package')

        eq(len(org_members), 0)

    def test_user_delete_marks_membership_of_group_as_deleted(self):
        sysadmin = factories.Sysadmin()
        group = factories.Group()
        user = factories.User()
        context = {'user': sysadmin['name']}

        member_dict = {
            'username': user['id'],
            'id': group['id'],
            'role': 'member'
        }
        helpers.call_action('group_member_create', context, **member_dict)

        group_members = helpers.call_action('member_list', context,
                                            id=group['id'],
                                            object_type='user',
                                            capacity='member')

        eq(len(group_members), 1)
        eq(group_members[0][0], user['id'])
        eq(group_members[0][1], 'user')

        helpers.call_action('user_delete', context, id=user['id'])

        group_members = helpers.call_action('member_list', context,
                                            id=group['id'],
                                            object_type='user',
                                            capacity='member')

        eq(len(group_members), 0)

    def test_user_delete_marks_membership_of_org_as_deleted(self):
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        user = factories.User()
        context = {'user': sysadmin['name']}

        member_dict = {
            'username': user['id'],
            'id': org['id'],
            'role': 'member'
        }
        helpers.call_action('organization_member_create', context,
                            **member_dict)

        org_members = helpers.call_action('member_list', context,
                                          id=org['id'],
                                          object_type='user',
                                          capacity='member')

        eq(len(org_members), 1)
        eq(org_members[0][0], user['id'])
        eq(org_members[0][1], 'user')

        helpers.call_action('user_delete', context, id=user['id'])

        org_members = helpers.call_action('member_list', context,
                                          id=org['id'],
                                          object_type='user',
                                          capacity='member')

        eq(len(org_members), 0)


class TestFollow(helpers.FunctionalTestBase):

    def test_followee_list(self):

        group1 = factories.Group(title='Finance')
        group2 = factories.Group(title='Environment')
        group3 = factories.Group(title='Education')

        user = factories.User()

        context = {'user': user['name']}

        helpers.call_action('follow_group', context, id=group1['id'])
        helpers.call_action('follow_group', context, id=group2['id'])

        followee_list = helpers.call_action('followee_list', context,
                                            id=user['name'])

        eq(len(followee_list), 2)
        eq(sorted([f['display_name'] for f in followee_list]),
           ['Environment', 'Finance'])

    def test_followee_list_with_q(self):

        group1 = factories.Group(title='Finance')
        group2 = factories.Group(title='Environment')
        group3 = factories.Group(title='Education')

        user = factories.User()

        context = {'user': user['name']}

        helpers.call_action('follow_group', context, id=group1['id'])
        helpers.call_action('follow_group', context, id=group2['id'])

        followee_list = helpers.call_action('followee_list', context,
                                            id=user['name'],
                                            q='E')

        eq(len(followee_list), 1)
        eq(followee_list[0]['display_name'], 'Environment')


class TestStatusShow(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckan.plugins'] = 'stats'

    def test_status_show(self):

        status = helpers.call_action(u'status_show')

        eq(status[u'ckan_version'], __version__)
        eq(status[u'site_url'], u'http://test.ckan.net')
        eq(status[u'site_title'], u'CKAN')
        eq(status[u'site_description'], u'')
        eq(status[u'locale_default'], u'en')

        eq(type(status[u'extensions']), list)
        eq(status[u'extensions'], [u'stats'])


class TestJobList(helpers.FunctionalRQTestBase):

    def test_all_queues(self):
        '''
        Test getting jobs from all queues.
        '''
        job1 = self.enqueue()
        job2 = self.enqueue()
        job3 = self.enqueue(queue=u'my_queue')
        jobs = helpers.call_action(u'job_list')
        eq(len(jobs), 3)
        eq({job[u'id'] for job in jobs}, {job1.id, job2.id, job3.id})

    def test_specific_queues(self):
        '''
        Test getting jobs from specific queues.
        '''
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u'q2')
        job3 = self.enqueue(queue=u'q3')
        job4 = self.enqueue(queue=u'q3')
        jobs = helpers.call_action(u'job_list', queues=[u'q2'])
        eq(len(jobs), 1)
        eq(jobs[0][u'id'], job2.id)
        jobs = helpers.call_action(u'job_list', queues=[u'q2', u'q3'])
        eq(len(jobs), 3)
        eq({job[u'id'] for job in jobs}, {job2.id, job3.id, job4.id})


class TestJobShow(helpers.FunctionalRQTestBase):

    def test_existing_job(self):
        '''
        Test showing an existing job.
        '''
        job = self.enqueue(queue=u'my_queue', title=u'Title')
        d = helpers.call_action(u'job_show', id=job.id)
        eq(d[u'id'], job.id)
        eq(d[u'title'], u'Title')
        eq(d[u'queue'], u'my_queue')
        ok(_seconds_since_timestamp(d[u'created'], u'%Y-%m-%dT%H:%M:%S') < 10)

    @nose.tools.raises(logic.NotFound)
    def test_not_existing_job(self):
        '''
        Test showing a not existing job.
        '''
        helpers.call_action(u'job_show', id=u'does-not-exist')


def _seconds_since_timestamp(timestamp, format_):
    dt = datetime.datetime.strptime(timestamp, format_)
    now = datetime.datetime.utcnow()
    assert now > dt  # we assume timestamp is not in the future
    return (now - dt).total_seconds()


class TestActivityShow(helpers.FunctionalTestBase):
    def test_simple_without_data(self):
        dataset = factories.Dataset()
        user = factories.User()
        activity = factories.Activity(
            user_id=user['id'], object_id=dataset['id'], revision_id=None,
            activity_type='new package',
            data={
                'package': copy.deepcopy(dataset),
                'actor': 'Mr Someone',
            })
        activity_shown = helpers.call_action(
            'activity_show', id=activity['id'], include_data=False)
        eq(activity_shown['user_id'], user['id'])
        ok(_seconds_since_timestamp(
            activity_shown['timestamp'], u'%Y-%m-%dT%H:%M:%S.%f') < 10)
        eq(activity_shown['object_id'], dataset['id'])
        eq(activity_shown['data'], {'package': {'title': 'Test Dataset'}})
        eq(activity_shown['activity_type'], u'new package')

    def test_simple_with_data(self):
        dataset = factories.Dataset()
        user = factories.User()
        activity = factories.Activity(
            user_id=user['id'], object_id=dataset['id'], revision_id=None,
            activity_type='new package',
            data={
                'package': copy.deepcopy(dataset),
                'actor': 'Mr Someone',
            })
        activity_shown = helpers.call_action(
            'activity_show', id=activity['id'], include_data=True)
        eq(activity_shown['user_id'], user['id'])
        ok(_seconds_since_timestamp(
            activity_shown['timestamp'], u'%Y-%m-%dT%H:%M:%S.%f') < 10)
        eq(activity_shown['object_id'], dataset['id'])
        eq(activity_shown['data'], {'package': dataset,
                                    'actor': 'Mr Someone'})
        eq(activity_shown['activity_type'], u'new package')


def _clear_activities():
    from ckan import model
    model.Session.query(model.ActivityDetail).delete()
    model.Session.query(model.Activity).delete()
    model.Session.flush()


class TestPackageActivityList(helpers.FunctionalTestBase):
    def test_create_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        assert_not_in('extras', activities[0]['data']['package'])

    def test_change_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)
        original_title = dataset['title']
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package', 'new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        eq(activities[0]['data']['package']['title'],
           'Dataset with changed title')

        # the old dataset still has the old title
        eq(activities[1]['activity_type'], 'new package')
        eq(activities[1]['data']['package']['title'], original_title)

    def test_change_dataset_add_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset['extras'].append(dict(key='rating', value='great'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        assert_not_in('extras', activities[0]['data']['package'])

    def test_change_dataset_change_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, extras=[
            dict(key='rating', value='great')])
        _clear_activities()
        dataset['extras'][0] = dict(key='rating', value='ok')
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        assert_not_in('extras', activities[0]['data']['package'])

    def test_change_dataset_delete_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, extras=[
            dict(key='rating', value='great')])
        _clear_activities()
        dataset['extras'] = []
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        assert_not_in('extras', activities[0]['data']['package'])

    def test_change_dataset_add_resource(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        resource = factories.Resource(package_id=dataset['id'], user=user)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        # NB the detail is not included - that is only added in by
        # activity_list_to_html()

    def test_change_dataset_change_resource(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, resources=[
            dict(url='https://example.com/foo.csv', format='csv')])
        _clear_activities()
        dataset['resources'][0]['format'] = 'pdf'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_delete_resource(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, resources=[
            dict(url='https://example.com/foo.csv', format='csv')])
        _clear_activities()
        dataset['resources'] = []
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_add_tag(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset['tags'].append(dict(name='checked'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_delete_tag_from_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user, tags=[dict(name='checked')])
        _clear_activities()
        dataset['tags'] = []
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_delete_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_private_dataset_has_no_activity(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(private=True,
                                    owner_org=org['id'], user=user)
        dataset['tags'] = []
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_private_dataset_delete_has_no_activity(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(private=True,
                                    owner_org=org['id'], user=user)
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def _create_bulk_package_activities(self, count):
        dataset = factories.Dataset()
        from ckan import model
        objs = [
            model.Activity(
                user_id=None, object_id=dataset['id'], revision_id=None,
                activity_type=None, data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return dataset['id']

    def test_limit_default(self):
        id = self._create_bulk_package_activities(35)
        results = helpers.call_action('package_activity_list', id=id)
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        id = self._create_bulk_package_activities(7)
        results = helpers.call_action('package_activity_list', id=id)
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        id = self._create_bulk_package_activities(9)
        results = helpers.call_action('package_activity_list', id=id, limit='9')
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action('package_activity_list',
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because dataset is created by site_user
        dataset = factories.Dataset()

        activities = helpers.call_action('package_activity_list',
                                         include_hidden_activity=True,
                                         id=dataset['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])


class TestUserActivityList(helpers.FunctionalTestBase):
    def test_create_user(self):
        user = factories.User()

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new user'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], user['id'])

    def test_create_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_dataset_changed_by_another_user(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset['extras'].append(dict(key='rating', value='great'))
        helpers.call_action(
            'package_update', context={'user': another_user['name']}, **dataset)

        # the user might have created the dataset, but a change by another
        # user does not show on the user's activity stream
        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_change_dataset_add_extra(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset['extras'].append(dict(key='rating', value='great'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_add_tag(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset['tags'].append(dict(name='checked'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_create_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'], group['title'])

    def test_delete_group_using_group_delete(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            'group_delete', context={'user': user['name']}, **group)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'], group['title'])

    def test_delete_group_by_updating_state(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group['state'] = 'deleted'
        helpers.call_action(
            'group_update', context={'user': user['name']}, **group)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'], group['title'])

    def test_create_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'], org['title'])

    def test_delete_org_using_organization_delete(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        helpers.call_action(
            'organization_delete', context={'user': user['name']}, **org)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'], org['title'])

    def test_delete_org_by_updating_state(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        org['state'] = 'deleted'
        helpers.call_action(
            'organization_update', context={'user': user['name']}, **org)

        activities = helpers.call_action('user_activity_list',
                                         id=user['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'], org['title'])

    def _create_bulk_user_activities(self, count):
        user = factories.User()
        from ckan import model
        objs = [
            model.Activity(
                user_id=user['id'], object_id=None, revision_id=None,
                activity_type=None, data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return user['id']

    def test_limit_default(self):
        id = self._create_bulk_user_activities(35)
        results = helpers.call_action('user_activity_list', id=id)
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        id = self._create_bulk_user_activities(7)
        results = helpers.call_action('user_activity_list', id=id)
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        id = self._create_bulk_user_activities(9)
        results = helpers.call_action('user_activity_list', id=id, limit='9')
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max


class TestGroupActivityList(helpers.FunctionalTestBase):
    def test_create_group(self):
        user = factories.User()
        group = factories.Group(user=user)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'], group['title'])

    def test_change_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)
        original_title = group['title']
        group['title'] = 'Group with changed title'
        helpers.call_action(
            'group_update', context={'user': user['name']}, **group)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed group', 'new group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'],
           'Group with changed title')

        # the old group still has the old title
        eq(activities[1]['activity_type'], 'new group')
        eq(activities[1]['data']['group']['title'], original_title)

    def test_create_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        original_title = dataset['title']
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package', 'new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

        # the old dataset still has the old title
        eq(activities[1]['activity_type'], 'new package')
        eq(activities[1]['data']['package']['title'], original_title)

    def test_change_dataset_add_extra(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        _clear_activities()
        dataset['extras'].append(dict(key='rating', value='great'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_add_tag(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        _clear_activities()
        dataset['tags'].append(dict(name='checked'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_delete_dataset(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        _clear_activities()
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_that_used_to_be_in_the_group(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        # remove the dataset from the group
        dataset['groups'] = []
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)
        _clear_activities()
        # edit the dataset
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        # dataset change should not show up in its former group
        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities], [])

    def test_delete_dataset_that_used_to_be_in_the_group(self):
        user = factories.User()
        group = factories.Group(user=user)
        dataset = factories.Dataset(groups=[{'id': group['id']}], user=user)
        # remove the dataset from the group
        dataset['groups'] = []
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)
        _clear_activities()
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        # NOTE:
        # ideally the dataset's deletion would not show up in its old group
        # but it can't be helped without _group_activity_query getting very
        # complicated
        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def _create_bulk_group_activities(self, count):
        group = factories.Group()
        from ckan import model
        objs = [
            model.Activity(
                user_id=None, object_id=group['id'], revision_id=None,
                activity_type=None, data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return group['id']

    def test_limit_default(self):
        id = self._create_bulk_group_activities(35)
        results = helpers.call_action('group_activity_list', id=id)
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        id = self._create_bulk_group_activities(7)
        results = helpers.call_action('group_activity_list', id=id)
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        id = self._create_bulk_group_activities(9)
        results = helpers.call_action('group_activity_list', id=id, limit='9')
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action('group_activity_list',
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because group is created by site_user
        group = factories.Group()

        activities = helpers.call_action('group_activity_list',
                                         include_hidden_activity=True,
                                         id=group['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new group'])


class TestOrganizationActivityList(helpers.FunctionalTestBase):
    def test_create_organization(self):
        user = factories.User()
        org = factories.Organization(user=user)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'], org['title'])

    def test_change_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)
        original_title = org['title']
        org['title'] = 'Organization with changed title'
        helpers.call_action(
            'organization_update', context={'user': user['name']}, **org)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed organization', 'new organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'],
           'Organization with changed title')

        # the old org still has the old title
        eq(activities[1]['activity_type'], 'new organization')
        eq(activities[1]['data']['group']['title'], original_title)

    def test_create_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org['id'], user=user)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        original_title = dataset['title']
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package', 'new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

        # the old dataset still has the old title
        eq(activities[1]['activity_type'], 'new package')
        eq(activities[1]['data']['package']['title'], original_title)

    def test_change_dataset_add_tag(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        _clear_activities()
        dataset['tags'].append(dict(name='checked'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_delete_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        _clear_activities()
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_that_used_to_be_in_the_org(self):
        user = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        # remove the dataset from the org
        dataset['owner_org'] = org2['id']
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)
        _clear_activities()
        # edit the dataset
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        # dataset change should not show up in its former group
        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities], [])

    def test_delete_dataset_that_used_to_be_in_the_org(self):
        user = factories.User()
        org = factories.Organization(user=user)
        org2 = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        # remove the dataset from the group
        dataset['owner_org'] = org2['id']
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)
        _clear_activities()
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        # dataset deletion should not show up in its former org
        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities], [])

    def _create_bulk_org_activities(self, count):
        org = factories.Organization()
        from ckan import model
        objs = [
            model.Activity(
                user_id=None, object_id=org['id'], revision_id=None,
                activity_type=None, data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return org['id']

    def test_limit_default(self):
        id = self._create_bulk_org_activities(35)
        results = helpers.call_action('organization_activity_list', id=id)
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        id = self._create_bulk_org_activities(7)
        results = helpers.call_action('organization_activity_list', id=id)
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        id = self._create_bulk_org_activities(9)
        results = helpers.call_action('organization_activity_list', id=id, limit='9')
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max

    def test_normal_user_doesnt_see_hidden_activities(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_doesnt_see_hidden_activities_by_default(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           [])

    def test_sysadmin_user_can_include_hidden_activities(self):
        # activity is 'hidden' because org is created by site_user
        org = factories.Organization()

        activities = helpers.call_action('organization_activity_list',
                                         include_hidden_activity=True,
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new organization'])


class TestRecentlyChangedPackagesActivityList(helpers.FunctionalTestBase):
    def test_create_dataset(self):
        user = factories.User()
        org = factories.Dataset(user=user)

        activities = helpers.call_action('recently_changed_packages_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['package']['title'], org['title'])

    def test_change_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        original_title = dataset['title']
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('recently_changed_packages_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package', 'new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

        # the old dataset still has the old title
        eq(activities[1]['activity_type'], 'new package')
        eq(activities[1]['data']['package']['title'], original_title)

    def test_change_dataset_add_extra(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        _clear_activities()
        dataset['extras'].append(dict(key='rating', value='great'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('recently_changed_packages_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_change_dataset_add_tag(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        _clear_activities()
        dataset['tags'].append(dict(name='checked'))
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('recently_changed_packages_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['changed package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def test_delete_dataset(self):
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(owner_org=org['id'], user=user)
        _clear_activities()
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)

        activities = helpers.call_action('organization_activity_list',
                                         id=org['id'])
        eq([activity['activity_type'] for activity in activities],
           ['deleted package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])

    def _create_bulk_package_activities(self, count):
        from ckan import model
        objs = [
            model.Activity(
                user_id=None, object_id=None, revision_id=None,
                activity_type='new_package', data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_package_activities(35)
        results = helpers.call_action('recently_changed_packages_activity_list')
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        self._create_bulk_package_activities(7)
        results = helpers.call_action('recently_changed_packages_activity_list')
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        self._create_bulk_package_activities(9)
        results = helpers.call_action('recently_changed_packages_activity_list', limit='9')
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max


class TestDashboardActivityList(helpers.FunctionalTestBase):
    def test_create_user(self):
        user = factories.User()

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([activity['activity_type'] for activity in activities],
           ['new user'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], user['id'])
        # user's own activities are always marked ``'is_new': False``
        eq(activities[0]['is_new'], False)

    def test_create_dataset(self):
        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([activity['activity_type'] for activity in activities],
           ['new package'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], dataset['id'])
        eq(activities[0]['data']['package']['title'], dataset['title'])
        # user's own activities are always marked ``'is_new': False``
        eq(activities[0]['is_new'], False)

    def test_create_group(self):
        user = factories.User()
        _clear_activities()
        group = factories.Group(user=user)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([activity['activity_type'] for activity in activities],
           ['new group'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], group['id'])
        eq(activities[0]['data']['group']['title'], group['title'])
        # user's own activities are always marked ``'is_new': False``
        eq(activities[0]['is_new'], False)

    def test_create_organization(self):
        user = factories.User()
        _clear_activities()
        org = factories.Organization(user=user)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([activity['activity_type'] for activity in activities],
           ['new organization'])
        eq(activities[0]['user_id'], user['id'])
        eq(activities[0]['object_id'], org['id'])
        eq(activities[0]['data']['group']['title'], org['title'])
        # user's own activities are always marked ``'is_new': False``
        eq(activities[0]['is_new'], False)

    def _create_bulk_package_activities(self, count):
        user = factories.User()
        from ckan import model
        objs = [
            model.Activity(
                user_id=user['id'], object_id=None, revision_id=None,
                activity_type=None, data=None)
            for i in range(count)]
        model.Session.add_all(objs)
        model.repo.commit_and_remove()
        return user['id']

    def test_limit_default(self):
        id = self._create_bulk_package_activities(35)
        results = helpers.call_action('dashboard_activity_list',
                                      context={'user': id})
        eq(len(results), 31)  # i.e. default value

    @helpers.change_config('ckan.activity_list_limit', '5')
    def test_limit_configured(self):
        id = self._create_bulk_package_activities(7)
        results = helpers.call_action('dashboard_activity_list',
                                      context={'user': id})
        eq(len(results), 5)  # i.e. ckan.activity_list_limit

    @helpers.change_config('ckan.activity_list_limit', '5')
    @helpers.change_config('ckan.activity_list_limit_max', '7')
    def test_limit_hits_max(self):
        id = self._create_bulk_package_activities(9)
        results = helpers.call_action('dashboard_activity_list', limit='9',
                                      context={'user': id})
        eq(len(results), 7)  # i.e. ckan.activity_list_limit_max


class TestDashboardNewActivities(helpers.FunctionalTestBase):
    def test_users_own_activities(self):
        # a user's own activities are not shown as "new"
        user = factories.User()
        dataset = factories.Dataset(user=user)
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': user['name']}, **dataset)
        helpers.call_action(
            'package_delete', context={'user': user['name']}, **dataset)
        group = factories.Group(user=user)
        group['title'] = 'Group with changed title'
        helpers.call_action(
            'group_update', context={'user': user['name']}, **group)
        helpers.call_action(
            'group_delete', context={'user': user['name']}, **group)

        new_activities = helpers.call_action('dashboard_activity_list',
                                             context={'user': user['id']})
        eq([activity['is_new'] for activity in new_activities],
           [False] * 7)
        new_activities_count = \
            helpers.call_action('dashboard_new_activities_count',
                                context={'user': user['id']})
        eq(new_activities_count, 0)

    def test_activities_by_a_followed_user(self):
        user = factories.User()
        followed_user = factories.User()
        helpers.call_action(
            'follow_user', context={'user': user['name']}, **followed_user)
        _clear_activities()
        dataset = factories.Dataset(user=followed_user)
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': followed_user['name']}, **dataset)
        helpers.call_action(
            'package_delete', context={'user': followed_user['name']}, **dataset)
        group = factories.Group(user=followed_user)
        group['title'] = 'Group with changed title'
        helpers.call_action(
            'group_update', context={'user': followed_user['name']}, **group)
        helpers.call_action(
            'group_delete', context={'user': followed_user['name']}, **group)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([activity['activity_type'] for activity in activities[::-1]],
           ['new package', 'changed package', 'deleted package',
            'new group', 'changed group', 'deleted group'])
        eq([activity['is_new'] for activity in activities],
           [True] * 6)
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           6)

    def test_activities_on_a_followed_dataset(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        _clear_activities()
        dataset = factories.Dataset(user=another_user)
        helpers.call_action(
            'follow_dataset', context={'user': user['name']}, **dataset)
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': another_user['name']}, **dataset)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([(activity['activity_type'], activity['is_new'])
            for activity in activities[::-1]],
           [('new package', True),
            # NB The 'new package' activity is in our activity stream and shows
            # as "new" even though it occurred before we followed it. This is
            # known & intended design.
            ('changed package', True),
            ])
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           2)

    def test_activities_on_a_followed_group(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        _clear_activities()
        group = factories.Group(user=user)
        helpers.call_action(
            'follow_group', context={'user': user['name']}, **group)
        group['title'] = 'Group with changed title'
        helpers.call_action(
            'group_update', context={'user': another_user['name']}, **group)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([(activity['activity_type'], activity['is_new'])
            for activity in activities[::-1]],
           [('new group', False),  # False because user did this one herself
            ('changed group', True),
            ])
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           1)

    def test_activities_on_a_dataset_in_a_followed_group(self):
        user = factories.User()
        another_user = factories.Sysadmin()
        group = factories.Group(user=user)
        _clear_activities()
        dataset = factories.Dataset(groups=[{'name': group['name']}],
                                    user=another_user)
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'follow_dataset', context={'user': user['name']}, **dataset)
        helpers.call_action(
            'package_update', context={'user': another_user['name']}, **dataset)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([(activity['activity_type'], activity['is_new'])
            for activity in activities[::-1]],
           [('new package', True),
            ('changed package', True),
            ])
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           2)

    def test_activities_that_should_not_show(self):
        user = factories.User()
        _clear_activities()
        # another_user does some activity unconnected with user
        another_user = factories.Sysadmin()
        group = factories.Group(user=another_user)
        dataset = factories.Dataset(groups=[{'name': group['name']}],
                                    user=another_user)
        dataset['title'] = 'Dataset with changed title'
        helpers.call_action(
            'package_update', context={'user': another_user['name']}, **dataset)

        activities = helpers.call_action('dashboard_activity_list',
                                         context={'user': user['id']})
        eq([(activity['activity_type'], activity['is_new'])
            for activity in activities[::-1]],
           [])
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           0)

    @helpers.change_config('ckan.activity_list_limit', '15')
    def test_maximum_number_of_new_activities(self):
        '''Test that the new activities count does not go higher than 15, even
        if there are more than 15 new activities from the user's followers.'''
        user = factories.User()
        another_user = factories.Sysadmin()
        dataset = factories.Dataset()
        helpers.call_action(
            'follow_dataset', context={'user': user['name']}, **dataset)
        for n in range(0, 20):
            dataset['notes'] = 'Updated {n} times'.format(n=n)
            helpers.call_action(
                'package_update', context={'user': another_user['name']}, **dataset)
        eq(helpers.call_action('dashboard_new_activities_count',
                               context={'user': user['id']}),
           15)
