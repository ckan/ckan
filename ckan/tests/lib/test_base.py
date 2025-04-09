# encoding: utf-8
import json

import pytest

import ckan.tests.factories as factories
import ckan.lib.helpers as h
from ckan.tests.helpers import CKANTestApp


def test_apitoken_missing(app):
    request_headers = {}
    data_dict = {"type": "dataset", "name": "a-name"}
    url = h.url_for(
            "api.action",
            logic_function="package_create",
            ver=3,
        )
    app.post(url, json=data_dict, headers=request_headers, status=403)


@pytest.mark.usefixtures("non_clean_db")
def test_apitoken_in_authorization_header(app):
    user = factories.Sysadmin()
    user_token = factories.APIToken(user=user["id"], context={})
    request_headers = {
        "Authorization": user_token
    }

    app.get("/dataset/new", headers=request_headers)


@pytest.mark.usefixtures("non_clean_db")
def test_apitoken_in_x_ckan_header(app):
    user = factories.Sysadmin()
    user_token = factories.APIToken(user=user["id"], context={})
    # non-standard header name is defined in test-core.ini
    request_headers = {"X-Non-Standard-CKAN-API-Key": user_token}

    app.get("/dataset/new", headers=request_headers)


def test_apitoken_contains_unicode(app):
    # there is no valid apitoken containing unicode, but we should fail
    # nicely if unicode is supplied
    request_headers = {"Authorization": "\xc2\xb7"}
    data_dict = {"type": "dataset", "name": "a-name"}
    url = h.url_for(
            "api.action",
            logic_function="package_create",
            ver=3,
        )
    app.post(url, json=data_dict, headers=request_headers, status=403)


def test_options(app):
    response = app.options(url="/", status=200)
    assert len(response.data) == 0, "OPTIONS must return no content"


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
        == "Authorization, Content-Type"
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
        == "Authorization, Content-Type"
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
        == "Authorization, Content-Type"
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


@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_options_2(app):
    response = app.options(url="/simple_url", status=200)
    assert len(response.data) == 0, "OPTIONS must return no content"


@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_no_cors_2(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response.
    """
    response = app.get("/simple_url")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_no_cors_with_origin(app):
    """
    No ckan.cors settings in config, so no Access-Control-Allow headers in
    response, even with origin header in request.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_url", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_true_no_origin_2(app):
    """
    With origin_allow_all set to true, but no origin in the request
    header, no Access-Control-Allow headers should be in the response.
    """
    response = app.get("/simple_url")
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_true_with_origin_2(app):
    """
    With origin_allow_all set to true, and an origin in the request
    header, the appropriate Access-Control-Allow headers should be in the
    response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_url", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" in response_headers
    assert response_headers["Access-Control-Allow-Origin"] == "*"
    assert (
        response_headers["Access-Control-Allow-Methods"]
        == "POST, PUT, GET, DELETE, OPTIONS"
    )
    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
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
    response = app.get("/simple_url", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://thirdpartyrequests.org"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_origin_allow_all_false_with_whitelisted_origin_2(app):
    """
    With origin_allow_all set to false, with an origin in the request
    header, and a whitelist defined (containing the origin), the
    appropriate Access-Control-Allow headers should be in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_url", headers=request_headers)
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
        == "Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist",
    "http://google.com http://thirdpartyrequests.org http://yahoo.co.uk",
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
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
    response = app.get("/simple_url", headers=request_headers)
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
        == "Authorization, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "true")
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("apitoken_header_name", "X-CKAN-API-TOKEN")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_cors_config_custom_auth_header(app):
    """
    When using a custom value for the auth header, this should be returned
    in the Access-Control-Allow-Headers header in the response.
    """
    request_headers = {"Origin": "http://thirdpartyrequests.org"}
    response = app.get("/simple_url", headers=request_headers)
    response_headers = dict(response.headers)

    assert (
        response_headers["Access-Control-Allow-Headers"]
        == "X-CKAN-API-TOKEN, Content-Type"
    )


@pytest.mark.ckan_config("ckan.cors.origin_allow_all", "false")
@pytest.mark.ckan_config(
    "ckan.cors.origin_whitelist", "http://google.com http://yahoo.co.uk"
)
@pytest.mark.ckan_config("ckan.site_url", "http://test.ckan.org")
@pytest.mark.ckan_config("ckan.plugins", "test_blueprint_plugin")
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
    response = app.get("/simple_url", headers=request_headers)
    response_headers = dict(response.headers)

    assert "Access-Control-Allow-Origin" not in response_headers
    assert "Access-Control-Allow-Methods" not in response_headers
    assert "Access-Control-Allow-Headers" not in response_headers


# Disable CSRF so we have a known session state
@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config('ckan.cache.public.enabled', False)
@pytest.mark.ckan_config('ckan.cache.private.enabled', True)
def test_cache_control_in_when_public_cache_is_not_enabled(app: CKANTestApp):
    request_headers = {}
    response = app.get('/', headers=request_headers)

    assert 'Cache-Control' in response.headers
    assert 'Set-Cookie' not in response.headers
    assert response.headers['Cache-Control'] == 'must-understand, private, max-age=60, stale-while-revalidate=0, stale-if-error=86400'


# Disable CSRF so we have a known session state
@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config('ckan.cache.public.enabled', True)
def test_cache_control_when_cache_enabled(app: CKANTestApp):
    request_headers = {}
    response = app.get('/', headers=request_headers)

    assert 'Cache-Control' in response.headers
    assert 'Set-Cookie' not in response.headers
    assert ('must-understand, public, max-age=3600, s-maxage=7200, stale-while-revalidate=0, stale-if-error=86400'
            == response.headers['Cache-Control'])


# Disable CSRF so we have a known session state
@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config('ckan.cache.public.enabled', True)
@pytest.mark.ckan_config('ckan.cache.expires', 300)
def test_cache_control_max_age_when_cache_enabled(app: CKANTestApp):
    request_headers = {}
    response = app.get('/', headers=request_headers)

    response_headers = response.headers

    assert 'Cache-Control' in response_headers
    assert 'public' in response_headers['Cache-Control']
    assert 'max-age=300' in response_headers['Cache-Control']


@pytest.mark.ckan_config('ckan.cache.public.enabled', 'true')
@pytest.mark.ckan_config('ckan.cache.private.enabled', 'true')
def test_cache_control_while_logged_in(app: CKANTestApp):
    # Collect client, so cookies persist for session
    client = app.test_client()
    user = factories.User(fullname="Logged-In-User", password="correct123")

    # get csrf input token via rest endpoint (also sets session cookie)
    csrf_object = json.loads(client.get(h.url_for("util.csrf_input")).get_data(as_text=True))

    identity = {"login": user["name"], "password": "correct123", csrf_object["name"]: csrf_object["value"]}
    response = client.post(h.url_for("user.login"), data=identity)

    # Verify we did log in
    assert "Logged-In-User" in response.get_data(as_text=True)

    # test client is too helpful and will automatically follow redirects for us,
    # need to look up response history for 302 header checks
    assert len(response.history) == 1
    assert 'Cache-Control' in response.history[0].headers
    assert response.history[0].headers['Cache-Control'] == 'must-understand, no-cache, max-age=0, no-store'
    assert 'Set-Cookie' in response.history[0].headers.keys()

    # Now test the page we were redirected to
    assert 'Set-Cookie' not in response.headers.keys()
    assert 'Cache-Control' in response.headers
    assert response.headers['Cache-Control'] == 'must-understand, private, max-age=60, stale-while-revalidate=0, stale-if-error=86400'


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config('ckan.cache.public.enabled', True)
@pytest.mark.ckan_config('ckan.cache.private.enabled', False)
def test_cache_control_while_logged_in_private_cache_disable(app: CKANTestApp):
    request_headers = {}
    response = app.get('/', headers=request_headers)

    assert 'Cache-Control' in response.headers
    assert ('must-understand, public, max-age=3600, s-maxage=7200, stale-while-revalidate=0, stale-if-error=86400'
            == response.headers['Cache-Control'])

    user = factories.User(password="correct123")
    identity = {"login": user["name"], "password": "correct123"}
    request_headers = {}

    response = app.post(
        h.url_for("user.login"), data=identity, headers=request_headers
    )
    response_headers = dict(response.headers)

    assert 'Cache-Control' in response_headers
    assert response_headers['Cache-Control'] == 'must-understand, no-cache, max-age=0, no-store'
