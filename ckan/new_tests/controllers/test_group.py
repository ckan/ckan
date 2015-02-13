from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.model as model
from ckan.new_tests import factories


class TestGroupController(helpers.FunctionalTestBase):

    def setup(self):
        model.repo.rebuild_db()

    def test_bulk_process_throws_404_for_nonexistent_org(self):
        app = self._get_test_app()
        bulk_process_url = url_for(controller='organization',
                                   action='bulk_process', id='does-not-exist')
        response = app.get(url=bulk_process_url, status=404)

    def test_page_thru_list_of_orgs(self):
        orgs = [factories.Organization() for i in range(35)]
        app = self._get_test_app()
        org_url = url_for(controller='organization', action='index')
        response = app.get(url=org_url)
        assert orgs[0]['name'] in response
        assert orgs[-1]['name'] not in response

        response2 = response.click('2')
        assert orgs[0]['name'] not in response2
        assert orgs[-1]['name'] in response2
