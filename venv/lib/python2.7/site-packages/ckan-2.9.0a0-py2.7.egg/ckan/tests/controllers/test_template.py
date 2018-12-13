# encoding: utf-8

from nose.tools import assert_equal

import ckan.tests.helpers as helpers


class TestTemplateController(helpers.FunctionalTestBase):

    def test_content_type(self):
        cases = {
            u'/robots.txt': u'text/plain; charset=utf-8',
            u'/page': u'text/html; charset=utf-8',
            u'/page.html': u'text/html; charset=utf-8',
        }
        app = self._get_test_app()
        for url, expected in cases.iteritems():
            response = app.get(url, status=200)
            assert_equal(response.headers.get(u'Content-Type'), expected)
