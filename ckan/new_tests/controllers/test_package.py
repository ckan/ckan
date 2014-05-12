from nose.tools import assert_equal
from routes import url_for as url_for

from ckan.new_tests.controllers import WsgiAppCase
import ckan.new_tests.factories as factories
import ckan.new_tests.helpers as helpers
import ckan.lib.search as search


class TestResourceRead(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        import ckan.model as model

        # Reset the db before each test method.
        model.repo.rebuild_db()

        # Clear the search index
        search.clear()

    def test_existing_resource_with_associated_package(self):
        new_package = factories.Dataset()
        resource = factories.Resource(package_id=new_package['id'])
        response = self.app.get(
            url=url_for(controller='package', action='resource_read',
            id=new_package['id'], resource_id=resource['id']),
            status=200,
        )

    def test_existing_resource_with_package_not_associated(self):
        new_package = factories.Dataset()
        resource = factories.Resource()
        response = self.app.get(
            url=url_for(controller='package', action='resource_read',
            id=new_package['id'], resource_id=resource['id']),
            status=404,
        )
