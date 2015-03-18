import nose.tools

import ckan.logic as logic
import ckan.plugins as p
import ckan.lib.search as search
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


eq = nose.tools.eq_


class TestGet(object):

    def setup(self):
        helpers.reset_db()

        # Clear the search index
        search.clear()

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
        # default is descending order

        eq(group_list, ['bb', 'aa'])

    def test_group_list_sort_by_package_count_ascending(self):

        factories.Group(name='aa')
        factories.Group(name='bb')
        factories.Dataset(groups=[{'name': 'aa'}, {'name': 'bb'}])
        factories.Dataset(groups=[{'name': 'aa'}])

        group_list = helpers.call_action('group_list',
                                         sort='package_count asc')

        eq(group_list, ['bb', 'aa'])

    def test_group_list_all_fields(self):

        group = factories.Group()

        group_list = helpers.call_action('group_list', all_fields=True)

        expected_group = dict(group.items()[:])
        for field in ('users', 'tags', 'extras', 'groups'):
            del expected_group[field]
        expected_group['packages'] = 0
        assert group_list[0] == expected_group
        assert 'extras' not in group_list[0]
        assert 'tags' not in group_list[0]
        assert 'groups' not in group_list[0]
        assert 'users' not in group_list[0]
        assert 'datasets' not in group_list[0]

    def test_group_list_extras_returned(self):

        group = factories.Group(extras=[{'key': 'key1', 'value': 'val1'}])

        group_list = helpers.call_action('group_list', all_fields=True,
                                         include_extras=True)

        eq(group_list[0]['extras'], group['extras'])
        eq(group_list[0]['extras'][0]['key'], 'key1')

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
        for field in ('users', 'tags', 'extras'):
            del expected_parent_group[field]
        expected_parent_group['capacity'] = u'public'
        expected_parent_group['packages'] = 0
        expected_parent_group['package_count'] = 0
        eq(child_group_returned['groups'], [expected_parent_group])

    def test_group_show(self):

        group = factories.Group(user=factories.User())

        group_dict = helpers.call_action('group_show', id=group['id'])

        # FIXME: Should this be returned by group_create?
        group_dict.pop('num_followers', None)
        assert group_dict == group

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

        group_dict = helpers.call_action('group_show', id=group['id'])

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

        assert not 'packages' in group_dict
        assert group_dict['package_count'] == 2

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

    def test_organization_show(self):

        org = factories.Organization()

        org_dict = helpers.call_action('organization_show', id=org['id'])

        # FIXME: Should this be returned by organization_create?
        org_dict.pop('num_followers', None)
        assert org_dict == org

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

        org_dict = helpers.call_action('organization_show', id=org['id'])

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

        org_dict = helpers.call_action('organization_show', id=org['id'])

        assert len(org_dict['packages']) == 1
        assert org_dict['packages'][0]['name'] == 'dataset_1'
        assert org_dict['package_count'] == 1

    def test_user_list_default_values(self):

        user = factories.User()

        got_users = helpers.call_action('user_list')
        remove_pseudo_users(got_users)

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
        remove_pseudo_users(got_users)

        assert len(got_users) == 1
        got_user = got_users[0]
        assert got_user['number_created_packages'] == 1
        assert got_user['number_of_edits'] == 2

    def test_user_list_excludes_deleted_users(self):

        user = factories.User()
        factories.User(state='deleted')

        got_users = helpers.call_action('user_list')
        remove_pseudo_users(got_users)

        assert len(got_users) == 1
        assert got_users[0]['name'] == user['name']

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

        assert len(got_user['datasets']) == 3
        datasets_got = set([user_['name'] for user_ in got_user['datasets']])
        assert dataset_deleted['name'] not in datasets_got
        assert got_user['number_created_packages'] == 3

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

        assert len(got_user['datasets']) == 3
        datasets_got = set([user_['name'] for user_ in got_user['datasets']])
        assert dataset_deleted['name'] not in datasets_got
        assert got_user['number_created_packages'] == 3

    def test_related_list_with_no_params(self):
        '''
        Test related_list with no parameters and default sort
        '''
        user = factories.User()
        related1 = factories.Related(user=user, featured=True)
        related2 = factories.Related(user=user, type='application')

        related_list = helpers.call_action('related_list')
        assert ([related1, related2] == related_list)

    def test_related_list_type_filter(self):
        '''
        Test related_list with type filter
        '''
        user = factories.User()
        related1 = factories.Related(user=user, featured=True)
        related2 = factories.Related(user=user, type='application')

        related_list = helpers.call_action('related_list',
                                           type_filter='application')
        assert ([related2] == related_list)

    def test_related_list_sorted(self):
        '''
        Test related_list with sort parameter
        '''
        user = factories.User()
        related1 = factories.Related(user=user, featured=True)
        related2 = factories.Related(user=user, type='application')

        related_list = helpers.call_action('related_list', sort='created_desc')
        assert ([related2, related1] == related_list)

    def test_related_list_invalid_sort_parameter(self):
        '''
        Test related_list with invalid value for sort parameter
        '''
        user = factories.User()
        related1 = factories.Related(user=user, featured=True)
        related2 = factories.Related(user=user, type='application')

        related_list = helpers.call_action('related_list', sort='invalid')
        assert ([related1, related2] == related_list)

    def test_related_list_featured(self):
        '''
        Test related_list with no featured filter
        '''
        user = factories.User()
        related1 = factories.Related(user=user, featured=True)
        related2 = factories.Related(user=user, type='application')

        related_list = helpers.call_action('related_list', featured=True)
        assert ([related1] == related_list)
        # TODO: Create related items associated with a dataset and test
        # related_list with them

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

    def test_package_autocomplete_does_not_return_private_datasets(self):

        user = factories.User()
        org = factories.Organization(user=user)
        dataset1 = factories.Dataset(user=user, owner_org=org['name'],
                                     title='Some public stuff')
        dataset2 = factories.Dataset(user=user, owner_org=org['name'],
                                     private=True, title='Some private stuff')

        package_list = helpers.call_action('package_autocomplete',
                                           q='some')
        eq(len(package_list), 1)

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
                                        context=context)

            assert private_dataset['id'] not in [dataset['id'] for dataset
                                                 in group['packages']], (
                "group_show() should never show private datasets")

    def test_package_search_on_resource_name(self):
        '''
        package_search() should allow searching on resource name field.
        '''
        resource_name = 'resource_abc'
        package = factories.Resource(name=resource_name)

        search_result = helpers.call_action('package_search', q='resource_abc')
        eq(search_result['results'][0]['resources'][0]['name'], resource_name)


class TestBadLimitQueryParameters(object):
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
            'user_activity_list_html',
            'package_activity_list_html',
            'group_activity_list_html',
            'organization_activity_list_html',
            'recently_changed_packages_activity_list_html',
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


class TestOrganizationListForUser(object):
    '''Functional tests for the organization_list_for_user() action function.'''

    def setup(self):
        helpers.reset_db()
        search.clear()

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

    def test_does_not_return_members(self):
        """

        By default organization_list_for_user() should not return organizations
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

        assert organizations == []

    def test_does_not_return_editors(self):
        """

        By default organization_list_for_user() should not return organizations
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

        assert organizations == []

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
        helpers.call_action('organization_delete', id=organization['id'])

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


def remove_pseudo_users(user_list):
    pseudo_users = set(('logged_in', 'visitor'))
    user_list[:] = [user for user in user_list
                    if user['name'] not in pseudo_users]
