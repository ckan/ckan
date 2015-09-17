'''Unit tests for ckan/logic/auth/create.py.

'''

from pylons import config
import mock
import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestUserInvite(object):

    def setup(self):
        helpers.reset_db()

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_invited_user_is_created_as_pending(self, _):
        invited_user = self._invite_user_to_group()

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_creates_user_with_valid_username(self, _):
        email = 'user$%+abc@email.com'
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith('user---abc'), invited_user

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_assigns_user_to_group_in_expected_role(self, _):
        role = 'admin'
        invited_user = self._invite_user_to_group(role=role)

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group()

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch('ckan.lib.mailer.send_invite')
    @mock.patch('random.SystemRandom')
    def test_works_even_if_username_already_exists(self, rand, _):
        rand.return_value.random.side_effect = [1000, 1000, 1000, 2000,
                                                3000, 4000, 5000]

        for _ in range(3):
            invited_user = self._invite_user_to_group(email='same@email.com')
            assert invited_user is not None, invited_user

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(logic.ValidationError)
    def test_requires_email(self, _):
        self._invite_user_to_group(email=None)

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(logic.ValidationError)
    def test_requires_role(self, _):
        self._invite_user_to_group(role=None)

    @mock.patch('ckan.lib.mailer.send_invite')
    @nose.tools.raises(logic.ValidationError)
    def test_requires_group_id(self, _):
        self._invite_user_to_group(group={'id': None})

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_name_lowercase_when_email_is_uppercase(self, _):
        invited_user = self._invite_user_to_group(email='Maria@example.com')

        assert_equals(invited_user.name.split('-')[0], 'maria')

    def _invite_user_to_group(self, email='user@email.com',
                              group=None, role='member'):
        user = factories.User()
        group = group or factories.Group(user=user)

        context = {
            'user': user['name']
        }
        params = {
            'email': email,
            'group_id': group['id'],
            'role': role
        }

        result = helpers.call_action('user_invite', context, **params)

        return model.User.get(result['id'])


class TestResourceViewCreate(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

        helpers.reset_db()

    def setup(self):
        helpers.reset_db()

    def test_resource_view_create(self):
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action('resource_view_create', context, **params)

        result.pop('id')
        result.pop('package_id')

        assert_equals(params, result)

    def test_requires_resource_id(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('resource_id')

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    def test_requires_title(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('title')

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    @mock.patch('ckan.lib.datapreview.get_view_plugin')
    def test_requires_view_type(self, get_view_plugin):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop('view_type')

        get_view_plugin.return_value = 'mock_view_plugin'

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    def test_raises_if_couldnt_find_resource(self):
        context = {}
        params = self._default_resource_view_attributes(resource_id='unknown')
        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    def test_raises_if_couldnt_find_view_extension(self):
        context = {}
        params = self._default_resource_view_attributes(view_type='unknown')
        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    @mock.patch('ckan.lib.datapreview')
    def test_filterable_views_dont_require_any_extra_fields(self, datapreview_mock):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action('resource_view_create', context, **params)

        result.pop('id')
        result.pop('package_id')

        assert_equals(params, result)

    @mock.patch('ckan.lib.datapreview')
    def test_filterable_views_converts_filter_fields_and_values_into_filters_dict(self, datapreview_mock):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            'filter_fields': ['country', 'weather', 'country'],
            'filter_values': ['Brazil', 'warm', 'Argentina']
        }
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action('resource_view_create', context, **params)
        expected_filters = {
            'country': ['Brazil', 'Argentina'],
            'weather': ['warm']
        }
        assert_equals(result['filters'], expected_filters)

    @mock.patch('ckan.lib.datapreview')
    def test_filterable_views_converts_filter_fields_and_values_to_list(self, datapreview_mock):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            'filter_fields': 'country',
            'filter_values': 'Brazil'
        }
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action('resource_view_create', context, **params)
        assert_equals(result['filter_fields'], ['country'])
        assert_equals(result['filter_values'], ['Brazil'])
        assert_equals(result['filters'], {'country': ['Brazil']})

    @mock.patch('ckan.lib.datapreview')
    def test_filterable_views_require_filter_fields_and_values_to_have_same_length(self, datapreview_mock):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            'filter_fields': ['country', 'country'],
            'filter_values': 'Brazil'
        }
        params = self._default_resource_view_attributes(**filters)
        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    def test_non_filterable_views_dont_accept_filter_fields_and_values(self):
        context = {}
        filters = {
            'filter_fields': 'country',
            'filter_values': 'Brazil'
        }
        params = self._default_resource_view_attributes(**filters)
        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_create', context, **params)

    def _default_resource_view_attributes(self, **kwargs):
        default_attributes = {
            'resource_id': factories.Resource()['id'],
            'view_type': 'image_view',
            'title': 'View',
            'description': 'A nice view'
        }

        default_attributes.update(kwargs)

        return default_attributes

    def _configure_datapreview_to_return_filterable_view(self, datapreview_mock):
        filterable_view = mock.MagicMock()
        filterable_view.info.return_value = {'filterable': True}
        datapreview_mock.get_view_plugin.return_value = filterable_view


class TestCreateDefaultResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

        helpers.reset_db()

    def setup(self):
        helpers.reset_db()

    @helpers.change_config('ckan.views.default_views', '')
    def test_add_default_views_to_dataset_resources(self):

        # New resources have no views
        dataset_dict = factories.Dataset(resources=[
            {
                'url': 'http://some.image.png',
                'format': 'png',
                'name': 'Image 1',
            },
            {
                'url': 'http://some.image.png',
                'format': 'png',
                'name': 'Image 2',
            },
        ])

        # Change default views config setting
        config['ckan.views.default_views'] = 'image_view'

        context = {
            'user': helpers.call_action('get_site_user')['name']
        }
        created_views = helpers.call_action(
            'package_create_default_resource_views',
            context,
            package=dataset_dict)

        assert_equals(len(created_views), 2)

        assert_equals(created_views[0]['view_type'], 'image_view')
        assert_equals(created_views[1]['view_type'], 'image_view')

    @helpers.change_config('ckan.views.default_views', '')
    def test_add_default_views_to_resource(self):

        # New resources have no views
        dataset_dict = factories.Dataset()
        resource_dict = factories.Resource(
            package_id=dataset_dict['id'],
            url='http://some.image.png',
            format='png',
        )

        # Change default views config setting
        config['ckan.views.default_views'] = 'image_view'

        context = {
            'user': helpers.call_action('get_site_user')['name']
        }
        created_views = helpers.call_action(
            'resource_create_default_resource_views',
            context,
            resource=resource_dict,
            package=dataset_dict)

        assert_equals(len(created_views), 1)

        assert_equals(created_views[0]['view_type'], 'image_view')

    @helpers.change_config('ckan.views.default_views', '')
    def test_add_default_views_to_resource_no_dataset_passed(self):

        # New resources have no views
        dataset_dict = factories.Dataset()
        resource_dict = factories.Resource(
            package_id=dataset_dict['id'],
            url='http://some.image.png',
            format='png',
        )

        # Change default views config setting
        config['ckan.views.default_views'] = 'image_view'

        context = {
            'user': helpers.call_action('get_site_user')['name']
        }
        created_views = helpers.call_action(
            'resource_create_default_resource_views',
            context,
            resource=resource_dict)

        assert_equals(len(created_views), 1)

        assert_equals(created_views[0]['view_type'], 'image_view')


class TestResourceCreate(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_resource_create(self):
        context = {}
        params = {
            'package_id': factories.Dataset()['id'],
            'url': 'http://data',
            'name': 'A nice resource',
        }
        result = helpers.call_action('resource_create', context, **params)

        id = result.pop('id')

        assert id

        params.pop('package_id')
        for key in params.keys():
            assert_equals(params[key], result[key])

    def test_it_requires_package_id(self):

        data_dict = {
            'url': 'http://data',
        }

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_create', **data_dict)

    def test_it_requires_url(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        data_dict = {
            'package_id': dataset['id']
        }

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_create', **data_dict)


class TestMemberCreate(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_group_member_creation(self):
        user = factories.User()
        group = factories.Group()

        new_membership = helpers.call_action(
            'group_member_create',
            id=group['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], group['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')

    def test_organization_member_creation(self):
        user = factories.User()
        organization = factories.Organization()

        new_membership = helpers.call_action(
            'organization_member_create',
            id=organization['id'],
            username=user['name'],
            role='member',
        )

        assert_equals(new_membership['group_id'], organization['id'])
        assert_equals(new_membership['table_name'], 'user')
        assert_equals(new_membership['table_id'], user['id'])
        assert_equals(new_membership['capacity'], 'member')


class TestDatasetCreate(helpers.FunctionalTestBase):

    def test_normal_user_cant_set_id(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': False,
        }
        assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'package_create',
            context=context,
            id='1234',
            name='test-dataset',
        )

    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'ignore_auth': False,
        }
        dataset = helpers.call_action(
            'package_create',
            context=context,
            id='1234',
            name='test-dataset',
        )
        assert_equals(dataset['id'], '1234')

    def test_id_cant_already_exist(self):
        dataset = factories.Dataset()
        user = factories.Sysadmin()
        assert_raises(
            logic.ValidationError,
            helpers.call_action,
            'package_create',
            id=dataset['id'],
            name='test-dataset',
        )


class TestGroupCreate(helpers.FunctionalTestBase):

    def test_create_group(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='test-group',
        )

        assert len(group['users']) == 1
        assert group['display_name'] == u'test-group'
        assert group['package_count'] == 0
        assert not group['is_organization']
        assert group['type'] == 'group'

    @nose.tools.raises(logic.ValidationError)
    def test_create_group_validation_fail(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='',
        )

    def test_create_group_return_id(self):
        import re

        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
            'return_id_only': True
        }

        group = helpers.call_action(
            'group_create',
            context=context,
            name='test-group',
        )

        assert isinstance(group, str)
        assert re.match('([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)', group)

    def test_create_matches_show(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        created = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        shown = helpers.call_action(
            'organization_show',
            context=context,
            id='test-organization',
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k


class TestOrganizationCreate(helpers.FunctionalTestBase):

    def test_create_organization(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        assert len(org['users']) == 1
        assert org['display_name'] == u'test-organization'
        assert org['package_count'] == 0
        assert org['is_organization']
        assert org['type'] == 'organization'

    @nose.tools.raises(logic.ValidationError)
    def test_create_organization_validation_fail(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='',
        )

    def test_create_organization_return_id(self):
        import re

        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
            'return_id_only': True
        }

        org = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        assert isinstance(org, str)
        assert re.match('([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)', org)

    def test_create_matches_show(self):
        user = factories.User()
        context = {
            'user': user['name'],
            'ignore_auth': True,
        }

        created = helpers.call_action(
            'organization_create',
            context=context,
            name='test-organization',
        )

        shown = helpers.call_action(
            'organization_show',
            context=context,
            id='test-organization',
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k


class TestUserCreate(helpers.FunctionalTestBase):

    def test_user_create_with_password_hash(self):
        sysadmin = factories.Sysadmin()
        context = {
            'user': sysadmin['name'],
        }

        user = helpers.call_action(
            'user_create',
            context=context,
            email='test@example.com',
            name='test',
            password_hash='pretend-this-is-a-valid-hash')

        user_obj = model.User.get(user['id'])
        assert user_obj.password == 'pretend-this-is-a-valid-hash'

    def test_user_create_password_hash_not_for_normal_users(self):
        normal_user = factories.User()
        context = {
            'user': normal_user['name'],
        }

        user = helpers.call_action(
            'user_create',
            context=context,
            email='test@example.com',
            name='test',
            password='required',
            password_hash='pretend-this-is-a-valid-hash')

        user_obj = model.User.get(user['id'])
        assert user_obj.password != 'pretend-this-is-a-valid-hash'
