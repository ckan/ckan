import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.logic as logic
import ckan.model as model

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestDelete:

    def setup(self):
        helpers.reset_db()

    def test_resource_delete(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        resource = factories.Resource(user=user)
        context = {}
        params = {'id': resource['id']}

        helpers.call_action('resource_delete', context, **params)

        # Not even a sysadmin can see it now
        assert_raises(logic.NotFound, helpers.call_action, 'resource_show',
                      {'user': sysadmin['name']}, **params)
        # It is still there but with state=deleted
        res_obj = model.Resource.get(resource['id'])
        assert_equals(res_obj.state, 'deleted')
