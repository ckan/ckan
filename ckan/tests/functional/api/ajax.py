from ckan.tests import TestController as ControllerTestCase
from ckan.tests import url_for

class TestAjaxAPI(ControllerTestCase):
    def test_package_create_slug(self):
        response = self.app.get(
            url=url_for(controller='apiv2/package', action='create_slug'),
            params={
               'title': u'A New Title * With & Funny CHARacters',
            },
            status=200,
        )
        self.assert_equal(response.body, '{"valid": true, "name": "a_new_title_with_funny_characters"}')
        self.assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_tag_autocomplete(self):
        self.assert_equal(
            url_for(controller='tag', action='autocomplete'),
            '/api/2/util/tag/autocomplete',
        )
        response = self.app.get(
            url=url_for(controller='tag', action='autocomplete'),
            params={
               'incomplete': u'ru',
            },
            status=200,
        )
        self.assert_equal(response.body, '{"ResultSet": {"Result": []}}')
        self.assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

