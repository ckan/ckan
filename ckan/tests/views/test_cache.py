import pytest
import re
import hashlib
from flask import Request, Response
from werkzeug.test import EnvironBuilder
from ckan.common import request

from ckan.tests.helpers import CKANTestApp
from werkzeug.test import TestResponse

import ckan.views as views

field_name = '_csrf_token'  # emulate WTF_CSRF_FIELD_NAME for regex verification check
pattern = fr'(?i)((?:_csrf_token|{field_name})[^>]*?\b(?:content|value)=|\bnonce=)["\'][^"\']+(["\'])'  # noqa: E501


def clean_dynamic_values(text):
    return re.sub(pattern, lambda m: m.group(1) + '="etag_removed"', text)


@pytest.mark.ckan_config("ckan.cache_enabled", True)
def test_sets_cache_control_headers_default(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed."""

    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__no_cache__') is None
        assert request.environ.get('__no_private_cache__') is None
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.public is True, updated_response
    assert updated_response.cache_control.max_age == 0, updated_response
    assert updated_response.cache_control.must_revalidate is True, updated_response


@pytest.mark.ckan_config("ckan.cache_enabled", True)
@pytest.mark.ckan_config("ckan.cache_expires", 3600)
def test_sets_cache_control_headers_with__no_private_cache__set(app: CKANTestApp):
    """Test that cache control headers are set correctly when caching is allowed with override on max-age."""

    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={'__no_private_cache__': True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__no_cache__') is None
        assert request.environ.get('__no_private_cache__') is True
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.public is True
    assert updated_response.cache_control.max_age == 3600
    assert updated_response.cache_control.must_revalidate is True


@pytest.mark.ckan_config("ckan.cache_expires", 0)
def test_disables_cache_when_no_cache_env_present(app: CKANTestApp):
    """Test that no-cache headers are set when `__no_cache__` is true and `__no_private_cache__` is true in the environment."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__no_cache__": True,
        '__no_private_cache__': True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__no_cache__') is True
        assert request.environ.get('__no_private_cache__') is True
        updated_response = views.set_cache_control_headers_for_response(response)

    assert updated_response.cache_control.no_cache is True
    assert updated_response.cache_control.no_store is True
    assert updated_response.cache_control.must_revalidate is True
    assert updated_response.cache_control.max_age == 0


@pytest.mark.ckan_config("ckan.cache_expires", 7200)
def test_sets_private_cache_when___no_cache__is_set_and_no_private_cache_env_present(app: CKANTestApp):
    """Test that private cache is set when `__no_private_cache__` is absent but `__no_cache__` is present."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__no_cache__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__no_cache__') is True
        assert request.environ.get('__no_private_cache__') is None
        updated_response = views.set_cache_control_headers_for_response(response)

    assert updated_response.cache_control.private is True
    assert updated_response.cache_control.public is False


@pytest.mark.ckan_config("ckan.cache_expires", 7200)
def test_sets_private_cache_when_no_private_cache_env_present(app: CKANTestApp):
    """Test that private cache is set when `__no_private_cache__` is not present but `__no_cache__` is present."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__no_cache__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__no_cache__') is True
        assert request.environ.get('__no_private_cache__') is None
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.private is True
    assert updated_response.cache_control.public is False


@pytest.mark.ckan_config("ckan.cache_expires", 1800)
def test_adds_vary_cookie_when_limit_cache_by_cookie_is_present(app: CKANTestApp):
    """Test that `Vary: Cookie` is added when `__limit_cache_by_cookie__` is in the environment."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        assert request.environ.get('__limit_cache_by_cookie__') is True
        updated_response = views.set_cache_control_headers_for_response(response)
    assert "Cookie" in updated_response.vary


@pytest.mark.ckan_config("ckan.cache_expires", 300)
def test_removes_pragma_header_if_present(app: CKANTestApp):
    """Test that the `Pragma` header is removed if present in the response."""
    builder = EnvironBuilder(path='/', method='GET', headers={}, environ_overrides={
        "__limit_cache_by_cookie__": True})
    env = builder.get_environ()
    Request(env)
    response = Response()  # dummy response

    with app.flask_app.request_context(env):  # only works if you have app.flask_app
        response.headers["Pragma"] = "no-cache"
        # recall for under test altered response
        updated_response = views.set_cache_control_headers_for_response(response)

    assert "Pragma" not in updated_response.headers


@pytest.mark.ckan_config("ckan.cache_etags", True)
def test_sets_etag_when_missing(app: CKANTestApp):
    """Test that ETag is set if missing in the response headers."""
    request_headers = {}
    response = app.get('/', headers=request_headers)
    #  updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)
    expected_etag = hashlib.md5(clean_dynamic_values(response.get_data(as_text=True)).encode()).hexdigest()
    assert response.headers["ETag"] == f'"{expected_etag}"'


@pytest.mark.ckan_config("ckan.cache_etags", True)
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
        updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)
    assert updated_response.headers["ETag"] == '"existing-etag"'


@pytest.mark.ckan_config("ckan.cache_etags", True)
@pytest.mark.ckan_config("ckan.cache_etags_notModified", True)
def test_returns_304_if_etag_matches(app: CKANTestApp):
    """Test that response is changed to 304 Not Modified if ETag matches request."""
    request_headers = {}
    response: TestResponse = app.get('/', headers=request_headers)
    # use previous response ETag on next call
    assert response.headers["Etag"] is not None, response.headers

    request_headers["if_none_match"] = response.headers["Etag"]
    updated_response: TestResponse = app.get('/', headers=request_headers)

    # should be called inline, no need to call independently.
    # updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)

    assert updated_response.status_code == 304, "original Etag was {}, second call etag was {}".format(response.headers["Etag"], updated_response.headers["Etag"])
    assert updated_response.get_data() == b""
    assert "Content-Length" not in updated_response.headers


@pytest.mark.ckan_config("ckan.cache_etags", True)
@pytest.mark.ckan_config("ckan.cache_etags_notModified", True)
def test_does_not_return_304_if_etag_does_not_match(app: CKANTestApp):
    """Test that response is not modified if request's If-None-Match does not match the ETag."""

    request_headers = {}
    clean_response: TestResponse = app.get('/', headers=request_headers)
    clean_response_data = clean_response.get_data(as_text=True)
    request_headers: dict = {"if_none_match": "some-other-etag"}
    updated_response: TestResponse = app.get('/', headers=request_headers)

    assert updated_response.status_code == 200, "should have received payload, not 304 as invalid etag was passed in"
    under_test_response_data = updated_response.get_data(as_text=True)
    assert clean_dynamic_values(clean_response_data) == clean_dynamic_values(under_test_response_data)
    assert updated_response.get_etag() == clean_response.get_etag(), "etag were not the same, got {}, original etag was {}".format(updated_response.get_etag(), clean_response.get_etag())
