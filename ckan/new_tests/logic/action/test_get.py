import nose.tools

import ckan.logic as logic
import ckan.lib.search as search
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


eq = nose.tools.eq_


class TestGet(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        import ckan.model as model

        # Reset the db before each test method.
        model.repo.rebuild_db()

        # Clear the search index
        search.clear()

    def test_group_list(self):

        group1 = factories.Group()
        group2 = factories.Group()

        group_list = helpers.call_action('group_list')

        assert (sorted(group_list) ==
                sorted([g['name'] for g in [group1, group2]]))

    def test_group_show(self):

        group = factories.Group()

        group_dict = helpers.call_action('group_show', id=group['id'])

        # FIXME: Should this be returned by group_create?
        group_dict.pop('num_followers', None)
        assert group_dict == group

    def test_group_show_packages_returned(self):

        user_name = helpers.call_action('get_site_user')['name']

        group = factories.Group()

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

        group = factories.Group()

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
