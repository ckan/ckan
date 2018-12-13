# encoding: utf-8

'''Unit tests for ckan/logic/auth/delete.py.

'''

import nose

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic.auth.delete as auth_delete
from ckan import model
import ckan.plugins as p


logic = helpers.logic
assert_equals = nose.tools.assert_equals


class TestResourceDelete(object):

    def setup(self):
        helpers.reset_db()

    def test_anon_cant_delete(self):
        context = {'user': None, 'model': model}
        params = {}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_delete', context=context, **params)

    def test_no_org_user_cant_delete(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        response = auth_delete.resource_delete(
            {'user': user['name'], 'model': model},
            {'id': dataset['resources'][0]['id']})

        assert_equals(response['success'], False)

    def test_org_user_can_delete(self):
        user = factories.User()
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        org = factories.Organization(users=org_users)
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()],
                                    user=user)

        response = auth_delete.resource_delete(
            {'user': user['name'], 'model': model, 'auth_user_obj': user},
            {'id': dataset['resources'][0]['id']})

        assert_equals(response['success'], True)


class TestResourceViewDelete(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def setup(self):
        helpers.reset_db()

    def test_anon_cant_delete(self):
        context = {'user': None, 'model': model}
        params = {}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_delete', context=context,
                                 **params)

    def test_no_org_user_cant_delete(self):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()])

        resource_view = factories.ResourceView(
            resource_id=dataset['resources'][0]['id']
        )

        context = {'user': user['name'], 'model': model}

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_delete', context=context,
                                 id=resource_view['id'])

    def test_org_user_can_delete(self):
        user = factories.User()
        org_users = [{'name': user['name'], 'capacity': 'editor'}]
        org = factories.Organization(users=org_users)
        dataset = factories.Dataset(owner_org=org['id'],
                                    resources=[factories.Resource()],
                                    user=user)

        resource_view = factories.ResourceView(
            resource_id=dataset['resources'][0]['id']
        )

        context = {'user': user['name'], 'model': model}

        response = helpers.call_auth('resource_view_delete', context=context,
                                     id=resource_view['id'])

        assert_equals(response, True)


class TestResourceViewClear(object):

    def test_anon_cant_clear(self):
        context = {'user': None, 'model': model}
        params = {}
        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_clear', context=context,
                                 **params)

    def test_normal_user_cant_clear(self):
        user = factories.User()

        context = {'user': user['name'], 'model': model}

        nose.tools.assert_raises(logic.NotAuthorized, helpers.call_auth,
                                 'resource_view_clear', context=context)

    def test_sysadmin_user_can_clear(self):
        user = factories.User(sysadmin=True)

        context = {'user': user['name'], 'model': model}
        response = helpers.call_auth('resource_view_clear', context=context)

        assert_equals(response, True)
