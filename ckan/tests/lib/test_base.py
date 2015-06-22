from nose import tools as nose_tools

import ckan.tests.helpers as helpers


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
