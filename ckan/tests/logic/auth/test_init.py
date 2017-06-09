# encoding: utf-8

import nose

import ckan.model as core_model
import ckan.logic as logic
import ckan.tests.helpers as helpers
import ckan.logic.auth as logic_auth


class TestGetObjectErrors(object):

    def _get_function(self, obj_type):
        _get_object_functions = {
            'package': logic_auth.get_package_object,
            'resource': logic_auth.get_resource_object,
            'user': logic_auth.get_user_object,
            'group': logic_auth.get_group_object,
        }
        return _get_object_functions[obj_type]

    def _get_object_in_context(self, obj_type):

        if obj_type == 'user':
            context = {'user_obj': 'a_fake_object'}
        else:
            context = {obj_type: 'a_fake_object'}

        obj = self._get_function(obj_type)(context)

        assert obj == 'a_fake_object'

    def _get_object_id_not_found(self, obj_type):

        nose.tools.assert_raises(logic.NotFound,
                                 self._get_function(obj_type),
                                 {'model': core_model},
                                 {'id': 'not_here'})

    def _get_object_id_none(self, obj_type):

        nose.tools.assert_raises(logic.ValidationError,
                                 self._get_function(obj_type),
                                 {'model': core_model}, {})

    def test_get_package_object_in_context(self):
        self._get_object_in_context('package')

    def test_get_resource_object_in_context(self):
        self._get_object_in_context('resource')

    def test_get_user_object_in_context(self):
        self._get_object_in_context('user')

    def test_get_group_object_in_context(self):
        self._get_object_in_context('group')

    def test_get_package_object_id_not_found(self):
        self._get_object_id_not_found('package')

    def test_get_resource_object_id_not_found(self):
        self._get_object_id_not_found('resource')

    def test_get_user_object_id_not_found(self):
        self._get_object_id_not_found('user')

    def test_get_group_object_id_not_found(self):
        self._get_object_id_not_found('group')

    def test_get_package_object_id_none(self):
        self._get_object_id_none('package')

    def test_get_resource_object_id_none(self):
        self._get_object_id_none('resource')

    def test_get_user_object_id_none(self):
        self._get_object_id_none('user')

    def test_get_group_object_id_none(self):
        self._get_object_id_none('group')


class TestGetObject(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        import ckan.model as model

        # Reset the db before each test method.
        model.repo.rebuild_db()

    def test_get_package_object_with_id(self):

        user_name = helpers.call_action('get_site_user')['name']
        dataset = helpers.call_action('package_create',
                                      context={'user': user_name},
                                      name='test_dataset')
        context = {'model': core_model}
        obj = logic_auth.get_package_object(context, {'id': dataset['id']})

        assert obj.id == dataset['id']
        assert context['package'] == obj

    def test_get_resource_object_with_id(self):

        user_name = helpers.call_action('get_site_user')['name']
        dataset = helpers.call_action('package_create',
                                      context={'user': user_name},
                                      name='test_dataset')
        resource = helpers.call_action('resource_create',
                                       context={'user': user_name},
                                       package_id=dataset['id'],
                                       url='http://foo')

        context = {'model': core_model}
        obj = logic_auth.get_resource_object(context, {'id': resource['id']})

        assert obj.id == resource['id']
        assert context['resource'] == obj

    def test_get_user_object_with_id(self):

        user_name = helpers.call_action('get_site_user')['name']
        user = helpers.call_action('user_create',
                                   context={'user': user_name},
                                   name='test_user',
                                   email='a@a.com',
                                   password='TestPassword1')
        context = {'model': core_model}
        obj = logic_auth.get_user_object(context, {'id': user['id']})

        assert obj.id == user['id']
        assert context['user_obj'] == obj

    def test_get_group_object_with_id(self):

        user_name = helpers.call_action('get_site_user')['name']
        group = helpers.call_action('group_create',
                                    context={'user': user_name},
                                    name='test_group')
        context = {'model': core_model}
        obj = logic_auth.get_group_object(context, {'id': group['id']})

        assert obj.id == group['id']
        assert context['group'] == obj
