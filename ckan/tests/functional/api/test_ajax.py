from nose.tools import assert_equal

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase
from ckan.tests import url_for

class TestAjaxApi(ControllerTestCase):
    @classmethod
    def setup(cls):
        model.repo.init_db()
                
    @classmethod
    def teardown(cls):
        CreateTestData.delete()
        
    def test_package_create_slug(self):
        response = self.app.get(
            url=url_for(controller='apiv2/package', action='create_slug'),
            params={
               'title': u'A New Title * With & Funny CHARacters',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": true, "name": "a-new-title-with-funny-characters"}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_tag_autocomplete(self):
        CreateTestData.create()

        url = url_for(controller='apiv2/package', action='autocomplete')
        assert_equal(url, '/api/2/util/tag/autocomplete')
        response = self.app.get(
            url=url,
            params={
               'incomplete': u'ru',
            },
            status=200,
        )
        assert_equal(response.body, '{"ResultSet": {"Result": [{"Name": "russian"}]}}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

