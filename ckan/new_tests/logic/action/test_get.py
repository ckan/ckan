import nose.tools

import ckan.logic as logic
import ckan.lib.search as search
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


eq = nose.tools.eq_


class TestGet(object):

    def setup(self):
        helpers.reset_db()

        # Clear the search index
        search.clear()

    def test_group_list(self):

        group1 = factories.Group()
        group2 = factories.Group()

        group_list = helpers.call_action('group_list')

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

    def test_user_get(self):

        user = factories.User()

        ## auth_ignored
        got_user = helpers.call_action('user_show', id=user['id'])

        assert 'password' not in got_user
        assert 'reset_key' not in got_user
        assert 'apikey' not in got_user
        assert 'email' not in got_user

        got_user = helpers.call_action('user_show',
                                       context={'keep_email': True},
                                       id=user['id'])

        assert got_user['email'] == user['email']
        assert 'apikey' not in got_user
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

        got_user = helpers.call_action('user_show',
                                       context={'keep_apikey': True},
                                       id=user['id'])

        assert 'email' not in got_user
        assert got_user['apikey'] == user['apikey']
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

        sysadmin = factories.User(sysadmin=True)

        got_user = helpers.call_action('user_show',
                                       context={'user': sysadmin['name']},
                                       id=user['id'])

        assert got_user['email'] == user['email']
        assert got_user['apikey'] == user['apikey']
        assert 'password' not in got_user
        assert 'reset_key' not in got_user

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
