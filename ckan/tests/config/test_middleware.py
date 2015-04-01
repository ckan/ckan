import ckan.tests.helpers as helpers

from nose.tools import assert_equals, assert_not_equals
from routes import url_for


class TestPylonsResponseCleanupMiddleware(helpers.FunctionalTestBase):
    @classmethod
    def _apply_config_changes(cls, config):
        config['ckan.use_pylons_response_cleanup_middleware'] = True

    def test_homepage_with_middleware_activated(self):
        '''Test the home page renders with the middleware activated

        We are just testing the home page renders without any troubles and that
        the middleware has not done anything strange to the response string'''
        app = self._get_test_app()
        response = app.get(url=url_for(controller='home', action='index'))

        assert_equals(200, response.status_int)
        # make sure we haven't overwritten the response too early.
        assert_not_equals(
            'response cleared by pylons response cleanup middleware',
            response.body
        )
