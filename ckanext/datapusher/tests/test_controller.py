import nose
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.tests.legacy as tests
from ckan.tests import helpers
import ckan.tests.factories as factories

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import rebuild_all_dbs, set_url_type


class TestController():
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        p.load('datapusher')
        engine = db.get_write_engine()
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        rebuild_all_dbs(cls.Session)
        p.unload('datastore')
        p.unload('datapusher')

    def test_resource_data(self):
        user = factories.User()
        dataset = factories.Dataset(creator_user_id=user['id'])
        resource = factories.Resource(package_id=dataset['id'],
                                      creator_user_id=user['id'])
        auth = {'Authorization': str(user['apikey'])}

        self.app.get(
            url='/dataset/{id}/resource_data/{resource_id}'
            .format(id=str(dataset['name']),
                    resource_id=str(resource['id'])),
            extra_environ=auth)
