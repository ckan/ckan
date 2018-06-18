# encoding: utf-8

from nose import tools as nose_tools

import ckan.tests.helpers as helpers

import ckan.plugins as p
import ckan.tests.factories as factories


class TestRenderSnippet(helpers.FunctionalTestBase):
    """
    Test ``ckan.lib.base.render_snippet``.
    """
    @helpers.change_config('debug', True)
    def test_comment_present_if_debug_true(self):
        response = self._get_test_app().get('/')
        assert '<!-- Snippet ' in response

    @helpers.change_config('debug', False)
    def test_comment_absent_if_debug_false(self):
        response = self._get_test_app().get('/')
        assert '<!-- Snippet ' not in response


class TestGetUserForApikey(helpers.FunctionalTestBase):

    def test_apikey_missing(self):
        app = self._get_test_app()
        request_headers = {}

        app.get('/dataset/new', headers=request_headers, status=403)

    def test_apikey_in_authorization_header(self):
        user = factories.Sysadmin()
        app = self._get_test_app()
        request_headers = {'Authorization': str(user['apikey'])}

        app.get('/dataset/new', headers=request_headers)

    def test_apikey_in_x_ckan_header(self):
        user = factories.Sysadmin()
        app = self._get_test_app()
        # non-standard header name is defined in test-core.ini
        request_headers = {'X-Non-Standard-CKAN-API-Key': str(user['apikey'])}

        app.get('/dataset/new', headers=request_headers)

    def test_apikey_contains_unicode(self):
        # there is no valid apikey containing unicode, but we should fail
        # nicely if unicode is supplied
        app = self._get_test_app()
        request_headers = {'Authorization': '\xc2\xb7'}

        app.get('/dataset/new', headers=request_headers, status=403)


class TestCORS(helpers.FunctionalTestBase):

    def test_options(self):
        app = self._get_test_app()
        response = app.options(url='/', status=200)
        assert len(str(response.body)) == 0, 'OPTIONS must return no content'

    def test_cors_config_no_cors(self):
        '''
        No ckan.cors settings in config, so no Access-Control-Allow headers in
        response.
        '''
        app = self._get_test_app()
        response = app.get('/')
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    def test_cors_config_no_cors_with_origin(self):
        '''
        No ckan.cors settings in config, so no Access-Control-Allow headers in
        response, even with origin header in request.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'true')
    def test_cors_config_origin_allow_all_true_no_origin(self):
        '''
        With origin_allow_all set to true, but no origin in the request
        header, no Access-Control-Allow headers should be in the response.
        '''
        app = self._get_test_app()
        response = app.get('/')
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'true')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_true_with_origin(self):
        '''
        With origin_allow_all set to true, and an origin in the request
        header, the appropriate Access-Control-Allow headers should be in the
        response.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], '*')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_origin_without_whitelist(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, but no whitelist defined, there should be no Access-Control-
        Allow headers in the response.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://thirdpartyrequests.org')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_whitelisted_origin(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defined (containing the origin), the
        appropriate Access-Control-Allow headers should be in the response.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], 'http://thirdpartyrequests.org')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://google.com http://thirdpartyrequests.org http://yahoo.co.uk')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_multiple_whitelisted_origins(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defining multiple allowed origins (containing
        the origin), the appropriate Access-Control-Allow headers should be in
        the response.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], 'http://thirdpartyrequests.org')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://google.com http://yahoo.co.uk')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_whitelist_not_containing_origin(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defining multiple allowed origins (but not
        containing the requesting origin), there should be no Access-Control-
        Allow headers in the response.
        '''
        app = self._get_test_app()
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = app.get('/', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers


class TestCORSFlask(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        super(TestCORSFlask, cls).setup_class()
        cls.app = cls._get_test_app()
        flask_app = cls.app.flask_app

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')
            plugin = p.get_plugin('test_routing_plugin')
            flask_app.register_blueprint(plugin.get_blueprint(),
                                         prioritise_rules=True)

    @classmethod
    def teardown_class(cls):
        super(TestCORSFlask, cls).teardown_class()
        p.unload('test_routing_plugin')

    def test_options(self):
        response = self.app.options(url='/simple_flask', status=200)
        assert len(str(response.body)) == 0, 'OPTIONS must return no content'

    def test_cors_config_no_cors(self):
        '''
        No ckan.cors settings in config, so no Access-Control-Allow headers in
        response.
        '''
        response = self.app.get('/simple_flask')
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    def test_cors_config_no_cors_with_origin(self):
        '''
        No ckan.cors settings in config, so no Access-Control-Allow headers in
        response, even with origin header in request.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'true')
    def test_cors_config_origin_allow_all_true_no_origin(self):
        '''
        With origin_allow_all set to true, but no origin in the request
        header, no Access-Control-Allow headers should be in the response.
        '''
        response = self.app.get('/simple_flask')
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'true')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_true_with_origin(self):
        '''
        With origin_allow_all set to true, and an origin in the request
        header, the appropriate Access-Control-Allow headers should be in the
        response.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], '*')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_origin_without_whitelist(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, but no whitelist defined, there should be no Access-Control-
        Allow headers in the response.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://thirdpartyrequests.org')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_whitelisted_origin(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defined (containing the origin), the
        appropriate Access-Control-Allow headers should be in the response.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], 'http://thirdpartyrequests.org')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://google.com http://thirdpartyrequests.org http://yahoo.co.uk')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_multiple_whitelisted_origins(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defining multiple allowed origins (containing
        the origin), the appropriate Access-Control-Allow headers should be in
        the response.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' in response_headers
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Origin'], 'http://thirdpartyrequests.org')
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Methods'], "POST, PUT, GET, DELETE, OPTIONS")
        nose_tools.assert_equal(response_headers['Access-Control-Allow-Headers'], "X-CKAN-API-KEY, Authorization, Content-Type")

    @helpers.change_config('ckan.cors.origin_allow_all', 'false')
    @helpers.change_config('ckan.cors.origin_whitelist', 'http://google.com http://yahoo.co.uk')
    @helpers.change_config('ckan.site_url', 'http://test.ckan.org')
    def test_cors_config_origin_allow_all_false_with_whitelist_not_containing_origin(self):
        '''
        With origin_allow_all set to false, with an origin in the request
        header, and a whitelist defining multiple allowed origins (but not
        containing the requesting origin), there should be no Access-Control-
        Allow headers in the response.
        '''
        request_headers = {'Origin': 'http://thirdpartyrequests.org'}
        response = self.app.get('/simple_flask', headers=request_headers)
        response_headers = dict(response.headers)

        assert 'Access-Control-Allow-Origin' not in response_headers
        assert 'Access-Control-Allow-Methods' not in response_headers
        assert 'Access-Control-Allow-Headers' not in response_headers
