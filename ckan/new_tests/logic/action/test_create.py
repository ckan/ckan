import nose.tools

import ckan.model as model
import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

eq = nose.tools.eq_


class TestResourceCreate(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_requires_url(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        data_dict = {
            'package_id': dataset['id']
        }

        nose.tools.assert_raises(logic.ValidationError,
                                 helpers.call_action,
                                 'resource_create', **data_dict)
