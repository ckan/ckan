import pytest
import re

from flask import Request, Response
from werkzeug.test import EnvironBuilder
from ckan.common import request, CacheType, session, g
from ckan.lib import helpers as h, base

from ckan.tests.helpers import CKANTestApp
from werkzeug.test import TestResponse

import ckan.views as views

field_name = '_csrf_token'  # emulate WTF_CSRF_FIELD_NAME for regex verification check
pattern = fr'(?i)((?:_csrf_token|{field_name})[^>]*?\b(?:content|value)=|\bnonce=)["\'][^"\']+(["\'])'  # noqa: E501


def clean_dynamic_values(text):
    return re.sub(pattern, lambda m: m.group(1) + '="etag_removed"', text)


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
def test_sets_cache_control_headers_default(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed."""

    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        h.set_cache_level(CacheType.PUBLIC)
        updated_response = views.set_cache_control_headers_for_response(response)
    assert ('must-understand, public, max-age=3600, s-maxage=7200, stale-while-revalidate=0, stale-if-error=86400' ==
            updated_response.headers['Cache-Control'])


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.cache.expires", 3600)
def test_sets_cache_control_headers_cache_expires(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        h.set_cache_level(CacheType.PUBLIC, True)
        updated_response = views.set_cache_control_headers_for_response(response)
    assert ('must-understand, public, max-age=3600, s-maxage=7200, stale-while-revalidate=0, stale-if-error=86400'
            == updated_response.headers['Cache-Control'])


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.cache.shared.expires", 1)
def test_sets_cache_control_headers_shared_cache_expires(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        assert h.set_cache_level(CacheType.PUBLIC, True) is CacheType.PUBLIC
        updated_response = views.set_cache_control_headers_for_response(response)
    assert ('must-understand, public, max-age=3600, s-maxage=1, stale-while-revalidate=0, stale-if-error=86400'
            == updated_response.headers['Cache-Control'])


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.cache.stale_while_revalidates", 1)
@pytest.mark.ckan_config("ckan.cache.stale_if_error", 2)
def test_sets_cache_control_headers_stale_config_settings(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        assert h.set_cache_level(CacheType.PUBLIC, True)
        updated_response = views.set_cache_control_headers_for_response(response)
    assert ('must-understand, public, max-age=3600, s-maxage=7200, stale-while-revalidate=1, stale-if-error=2'
            == updated_response.headers['Cache-Control'])


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.stale-while-revalidate", 0)
@pytest.mark.ckan_config("ckan.cache.stale_if_error", 0)
def test_sets_cache_control_headers_stale_config_settings_disable(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        assert h.set_cache_level(CacheType.PUBLIC, True)
        updated_response = views.set_cache_control_headers_for_response(response)
    assert 'must-understand, public, max-age=3600, s-maxage=7200, must-revalidate' == updated_response.headers['Cache-Control']


@pytest.mark.ckan_config("ckan.cache.private.expires", 1234)
def test_sets_cache_control_headers_private_cache_expires(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = False
        assert h.set_cache_level(CacheType.PRIVATE, True)
        updated_response = views.set_cache_control_headers_for_response(response)
    assert 'must-understand, private, max-age=1234, stale-while-revalidate=0, stale-if-error=86400' == updated_response.headers['Cache-Control']


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.cache.public.enabled", False)
def test_cache_enabled_false_defaults_to_private(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""
    builder = EnvironBuilder(path='/', method='GET')
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        session.accessed = False
        session.modified = False  # CSRF is getting in the way of testing public overrides, disable session for now
        base._allow_caching()
        assert h.cache_level() == CacheType.PRIVATE
        updated_response = views.set_cache_control_headers_for_response(response)
    assert 'must-understand, private, max-age=60, stale-while-revalidate=0, stale-if-error=86400' == updated_response.headers['Cache-Control']


@pytest.mark.ckan_config("WTF_CSRF_ENABLED", False)
@pytest.mark.ckan_config("ckan.cache.public.enabled", False)
@pytest.mark.ckan_config("ckan.cache.private.enabled", False)
def test_cache_enabled_false_private_enabled_false_defaults_to_no_cache(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is not allowed."""
    response = app.get(h.url_for("/"))
    assert 'must-understand, no-cache, max-age=0' == response.headers['Cache-Control']


# Vary testing

def test_adds_vary_cookie_when_limit_cache_by_cookie_is_present(app: CKANTestApp):
    """Test that `Vary: Cookie` is added when `__limit_cache_by_cookie__` is in the environment."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        assert request.environ.get('__limit_cache_by_cookie__') is True
        updated_response = views.set_cache_control_headers_for_response(response)
    assert "Cookie" in updated_response.vary
    assert "HX-Request" in updated_response.vary


def test_adds_vary_cookie_when_g_limit_cache_for_page_is_true(app: CKANTestApp):
    """Test that `Vary: Cookie` is added when `__limit_cache_by_cookie__` is in the environment."""
    builder = EnvironBuilder(path='/', method='GET', headers={},)
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        with app.flask_app.app_context() as ctx:
            g.__session_was_empty = True
            assert request.environ.get('__limit_cache_by_cookie__') is None
            base._allow_caching()
            assert ctx.g.limit_cache_for_page is True
            updated_response = views.set_cache_control_headers_for_response(response)
    assert "Cookie" in updated_response.vary
    assert "HX-Request" in updated_response.vary


def test_removes_pragma_header_if_present(app: CKANTestApp):
    """Test that the `Pragma` header is removed if present in the response."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        g.__session_was_empty = True
        response.headers["Pragma"] = "no-cache"
        # recall for under test altered response
        updated_response = views.set_cache_control_headers_for_response(response)

    assert "Pragma" not in updated_response.headers


# Etag testing
@pytest.mark.ckan_config("ckan.etags.enabled", False)
def test_etag_not_set_when_config_disables_it(app: CKANTestApp):
    """Test that ETag is set if missing in the response headers."""
    request_headers = {}
    response = app.get('/', headers=request_headers)
    assert "ETag" not in response.headers, response.headers


@pytest.mark.ckan_config("ckan.etags.enabled", True)
def test_sets_etag_when_missing(app: CKANTestApp):
    """Test that ETag is set if missing in the response headers."""
    request_headers = {}
    response = app.get('/', headers=request_headers)
    assert response.headers["ETag"] is not None


@pytest.mark.ckan_config("ckan.etags.enabled", True)
def test_does_not_modify_etag_if_already_set(app: CKANTestApp):
    """Test that an existing ETag is not modified."""

    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        response.headers["ETag"] = '"existing-etag"'
        # recall set_etag_and_fast_304_response_if_unchanged again eith different etag to verify that it does not override
        updated_response = views.set_etag_for_response(response)
    assert updated_response.headers["ETag"] == '"existing-etag"'


@pytest.mark.ckan_config("ckan.etags.enabled", True)
def test_returns_304_if_etag_matches(app: CKANTestApp):
    """Test that response is changed to 304 Not Modified if ETag matches request."""
    request_headers = {}
    with app.flask_app.app_context() as ctx:
        ctx.g.etag_modified_time = "fixed"
        response: TestResponse = app.get('/', headers=request_headers)
    # use previous response ETag on next call
    assert response.headers["Etag"] is not None, response.headers

    with app.flask_app.app_context() as ctx:
        ctx.g.etag_modified_time = "fixed"  # expecting fixed-11683-3145776
        request_headers["if_none_match"] = response.headers["Etag"]
        updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.status_code == 304, "original Etag was {}, second call etag was {}".format(response.headers["Etag"], updated_response.headers["Etag"])
        assert updated_response.get_data() == b""
        assert "Content-Length" not in updated_response.headers

    with app.flask_app.app_context() as ctx:
        request_headers["if_none_match"] = response.headers["Etag"]
        # Due to hash system always different, we fix it for this test
        ctx.g.etag_replace = response.headers["Etag"].replace('"', '',)
        updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.status_code == 304, "original Etag was {}, second call etag was {}".format(response.headers["Etag"], updated_response.headers["Etag"])
        assert updated_response.get_data() == b""
        assert "Content-Length" not in updated_response.headers


@pytest.mark.ckan_config("ckan.etags.enabled", True)
def test_does_not_return_304_if_etag_does_not_match(app: CKANTestApp):
    """Test that response is not modified if request's If-None-Match does not match the ETag."""

    request_headers = {}
    clean_response: TestResponse = app.get('/', headers=request_headers)
    clean_response_data = clean_response.get_data(as_text=True)
    request_headers: dict = {"if_none_match": "some-other-etag"}
    updated_response: TestResponse = app.get('/', headers=request_headers)

    assert updated_response.status_code == 200
    under_test_response_data = updated_response.get_data(as_text=True)
    assert clean_dynamic_values(clean_response_data) == clean_dynamic_values(under_test_response_data)
    assert updated_response.get_etag() != clean_response.get_etag(), "etag were not the same, got {}, original etag was {}".format(updated_response.get_etag(), clean_response.get_etag())


def streaming_generator():
    yield b"streaming response data"


@pytest.mark.ckan_config("ckan.etags.enabled", True)
def test_does_not_add_etag_if_streaming_response_encountered(app: CKANTestApp):
    """Test that response is not modified if request's If-None-Match does not match the ETag."""
    from types import GeneratorType
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response(streaming_generator(), mimetype='text/plain')

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        # Ensure it is detected as streamed prior to calling function under test
        assert response.is_streamed
        assert isinstance(response.response, GeneratorType)

        # recall set_etag_and_fast_304_response_if_unchanged again eith different etag to verify that it does not override
        updated_response = views.set_etag_for_response(response)
    assert "ETag" not in updated_response.headers, updated_response.headers
