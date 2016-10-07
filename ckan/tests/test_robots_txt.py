# encoding: utf-8

from nose.tools import assert_equal, ok_

import ckan.tests.helpers as helpers


class TestRobotsTxt(helpers.FunctionalTestBase):

    def test_robots_txt(self):
        app = self._get_test_app()
        response = app.get(u'/robots.txt', status=200)
        assert_equal(response.headers.get(u'Content-Type'), u'text/plain; charset=utf-8')
        ok_(u'User-agent' in response)
