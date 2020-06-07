# encoding: utf-8

import six
import pytest
import ckan.tests.helpers as helpers

import ckan.plugins as p
import ckan.tests.factories as factories


@pytest.mark.ckan_config("debug", True)
def test_comment_present_if_debug_true(app):
    response = app.get("/")
    assert "<!-- Snippet " in response


@pytest.mark.ckan_config("debug", False)
def test_comment_absent_if_debug_false(app):
    response = app.get("/")
    assert "<!-- Snippet " not in response


def test_apikey_missing(app):
    request_headers = {}

    app.get("/dataset/new", headers=request_headers, status=403)


@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_apikey_in_authorization_header(app):
    user = factories.Sysadmin()
    request_headers = {"Authorization": str(user["apikey"])}

    app.get("/dataset/new", headers=request_headers)


@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_apikey_in_x_ckan_header(app):
    user = factories.Sysadmin()
    # non-standard header name is defined in test-core.ini
    request_headers = {"X-Non-Standard-CKAN-API-Key": str(user["apikey"])}

    app.get("/dataset/new", headers=request_headers)


def test_apikey_contains_unicode(app):
    # there is no valid apikey containing unicode, but we should fail
    # nicely if unicode is supplied
    request_headers = {"Authorization": "\xc2\xb7"}

    app.get("/dataset/new", headers=request_headers, status=403)


def test_options(app):
    response = app.options(url="/", status=200)
    assert len(six.ensure_str(response.data)) == 0, "OPTIONS must return no content"


def test_cors_config_no_cors(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response.
    """
    response = app.get("/")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


def test_cors_config_no_cors_with_origin_2(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response, even with origin header in request.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
def test_cors_config_origin_allow_all_true_no_origin(app):
    """
    With origin_allow_all set to true, but no origin in the request
    header, no Access-Control-Allow headers should be in the response.
    """
    response = app.get("/")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
def test_cors_config_origin_allow_all_true_with_origin(app):
    """
    With origin_allow_all set to true, and an origin in the request
    header, the appropriate Access-Control-Allow headers should be in the
    response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert response_headers["Access-Control-Allow-Origin"] == "*"
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
def test_cors_config_origin_allow_all_false_with_origin_without_whitelist(app):
    """
    With origin_allow_all set to false, with an origin in the request
    header, but no whitelist defined, there should be no Access-Control-
    Allow headers in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://thirdpartyrequests.org"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
def test_cors_config_origin_allow_all_false_with_whitelisted_origin(app):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defined (containing the origin), the
    appropriate Access-Control-Allow headers should be in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert (
        response_headers["Access-Control-Allow-Origin"]
        == "http://thirdpartyrequests.org"
    )
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist",
    "http://google.com http://thirdpartyrequests.org http://yahoo.co.uk",
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
def test_cors_config_origin_allow_all_false_with_multiple_whitelisted_origins(
    app,
):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defining multiple allowed origins (containing
    the origin), the appropriate Access-Control-Allow headers should be in
    the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert (
        response_headers["Access-Control-Allow-Origin"]
        == "http://thirdpartyrequests.org"
    )
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://google.com http://yahoo.co.uk"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
def test_cors_config_origin_allow_all_false_with_whitelist_not_containing_origin(
    app,
):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defining multiple allowed origins (but not
    containing the requesting origin), there should be no Access-Control-
    Allow headers in the response.
    """

    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_options_2(app):
    response = app.options(url="/simple_flask", status=200)
    assert len(six.ensure_str(response.data)) == 0, "OPTIONS must return no content"


@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_no_cors_2(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response.
    """
    response = app.get("/simple_flask")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_no_cors_with_origin(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response, even with origin header in request.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_true_no_origin_2(app):
    """
    With origin_allow_all set to true, but no origin in the request
    header, no Access-Control-Allow headers should be in the response.
    """
    response = app.get("/simple_flask")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_true_with_origin_2(app):
    """
    With origin_allow_all set to true, and an origin in the request
    header, the appropriate Access-Control-Allow headers should be in the
    response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert response_headers["Access-Control-Allow-Origin"] == "*"
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_false_with_origin_without_whitelist_2(
    app,
):
    """
    With origin_allow_all set to false, with an origin in the request
    header, but no whitelist defined, there should be no Access-Control-
    Allow headers in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://thirdpartyrequests.org"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_false_with_whitelisted_origin_2(app):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defined (containing the origin), the
    appropriate Access-Control-Allow headers should be in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert (
        response_headers["Access-Control-Allow-Origin"]
        == "http://thirdpartyrequests.org"
    )
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist",
    "http://google.com http://thirdpartyrequests.org http://yahoo.co.uk",
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_false_with_multiple_whitelisted_origins_2(
    app,
):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defining multiple allowed origins (containing
    the origin), the appropriate Access-Control-Allow headers should be in
    the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert (
        response_headers["Access-Control-Allow-Origin"]
        == "http://thirdpartyrequests.org"
    )
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-KEY, Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://google.com http://yahoo.co.uk"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_routing_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_false_with_whitelist_not_containing_origin_2(
    app,
):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defining multiple allowed origins (but not
    containing the requesting origin), there should be no Access-Control-
    Allow headers in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_flask", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config('ckan.cache_enabled', 'false')
def test_cache_control_in_when_cache_is_not_enabled(app):
    request_headers = {}
    response = app.get('/', headers=request_headers)
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert response_headers['Cache-Control'] == 'private'


@pytest.mark.ckan_config('ckan.cache_enabled', 'true')
def test_cache_control_when_cache_enabled(app):
    request_headers = {}
    response = app.get('/', headers=request_headers)
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert 'public' in response_headers['Cache-Control']


@pytest.mark.ckan_config('ckan.cache_enabled', 'true')
@pytest.mark.ckan_config('ckan.cache_expires', 300)
def test_cache_control_max_age_when_cache_enabled(app):
    request_headers = {}
    response = app.get('/', headers=request_headers)
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert 'public' in response_headers['Cache-Control']
    assert 'max-age=300' in response_headers['Cache-Control']


@pytest.mark.ckan_config('ckan.cache_enabled', None)
def test_cache_control_when_cache_is_not_set_in_config(app):
    request_headers = {}
    response = app.get('/', headers=request_headers)
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert response_headers['Cache-Control'] == 'private'


@pytest.mark.ckan_config('ckan.cache_enabled', 'true')
def test_cache_control_while_logged_in(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    request_headers = {}
    response = app.get('/', headers=request_headers, extra_environ=env)
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert response_headers['Cache-Control'] == 'private'
