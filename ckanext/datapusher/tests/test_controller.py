# encoding: utf-8

import nose

import ckan.tests.legacy as tests
from ckan.tests.helpers import FunctionalTestBase
import ckan.tests.factories as factories


class TestController(FunctionalTestBase):
    sysadmin_user = None
    normal_user = None

    _load_plugins = [u'datastore', u'datapusher']

    @classmethod
    def setup_class(cls):
        cls.app = cls._get_test_app()
        if not tests.is_datastore_supported():
            raise nose.SkipTest(u'Datastore not supported')
        super(TestController, cls).setup_class()

    def test_resource_data(self):
        user = factories.User()
        dataset = factories.Dataset(creator_user_id=user['id'])
        resource = factories.Resource(package_id=dataset['id'],
                                      creator_user_id=user['id'])
        auth = {u'Authorization': str(user['apikey'])}

        self.app.get(
            url=u'/dataset/{id}/resource_data/{resource_id}'
            .format(id=str(dataset['name']),
                    resource_id=str(resource['id'])),
            extra_environ=auth)
