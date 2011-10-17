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
        model.repo.rebuild_db()
        
    def test_package_slug_valid(self):
        CreateTestData.create()
        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid'),
            params={
               'type': u'package',
               'slug': u'A New Title * With & Funny CHARacters',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": true}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid'),
            params={
               'type': u'package',
               'slug': u'warandpeace',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": false}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_tag_autocomplete(self):
        CreateTestData.create()

        url = url_for(controller='api', action='tag_autocomplete')
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

