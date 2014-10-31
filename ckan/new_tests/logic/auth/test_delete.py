
'''Unit tests for ckan/logic/auth/delete.py.

'''

import nose

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic.auth.delete as auth_delete
from ckan import model

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
            {'user': user['name'], 'model': model},
            {'id': dataset['resources'][0]['id']})

        assert_equals(response['success'], True)
