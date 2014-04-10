import nose.tools

import ckan.model as model
import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

eq = nose.tools.eq_


class TestCreate(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_resource_create(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        url = 'http://ckan.org/data.csv'
        data_dict = {
            'package_id': dataset['id'],
            'url': url
        }

        resource = helpers.call_action('resource_create', **data_dict)

        assert resource is not None
        eq(resource['url'], url)

    def test_resource_create_requires_package_id(self):
        url = 'http://ckan.org/data.csv'
        data_dict = {
            'url': url
        }

        nose.tools.assert_raises(logic.ValidationError,
                                 helpers.call_action,
                                 'resource_create', **data_dict)

    def test_resource_create_requires_url(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        data_dict = {
            'package_id': dataset['id']
        }

        nose.tools.assert_raises(logic.ValidationError,
                                 helpers.call_action,
                                 'resource_create', **data_dict)

    def test_resource_create_validates_created_date(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)
        url = 'http://ckan.org/data.csv'
        data_dict = {
            'package_id': dataset['id'],
            'url': url,
            'created': 'invalid_date'
        }

        nose.tools.assert_raises(logic.ValidationError,
                                 helpers.call_action,
                                 'resource_create', **data_dict)
