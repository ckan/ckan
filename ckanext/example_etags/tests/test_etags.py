import pytest
import re
import hashlib
from flask import Request, Response
from werkzeug.test import EnvironBuilder
from ckan.lib.helpers import url_for
from ckan.tests import factories

from ckan.tests.helpers import CKANTestApp
from werkzeug.test import TestResponse

import ckan.views as views

field_name = '_csrf_token'  # emulate WTF_CSRF_FIELD_NAME for regex verification check
pattern = fr'(?i)((?:_csrf_token|{field_name})[^>]*?\b(?:content|value)=|\bnonce=)["\'][^"\']+(["\'])'  # noqa: E501


def clean_dynamic_values(text):
    return re.sub(pattern, lambda m: m.group(1) + '="etag_removed"', text)


def streaming_generator():
    yield b"streaming response data"


@pytest.mark.ckan_config(u'ckan.plugins', u'etags')
@pytest.mark.usefixtures(u'with_plugins', u'etags')
@pytest.mark.ckan_config("ckan.etags.enabled", True)
class test_etag_plugins():

    @pytest.mark.ckan_config("ckan.etags.enabled", False)
    def test_etag_not_set_when_config_disables_it(self, app: CKANTestApp):
        """Test that ETag is set if missing in the response headers."""
        request_headers = {}
        response = app.get('/', headers=request_headers)
        assert "ETag" not in response.headers, response.headers

    def test_sets_etag_when_missing(self, app: CKANTestApp):
        """Test that ETag is set if missing in the response headers."""
        request_headers = {}
        response = app.get('/', headers=request_headers)
        expected_etag = hashlib.md5(clean_dynamic_values(response.get_data(as_text=True)).encode()).hexdigest()
        assert response.headers["ETag"] == f'"{expected_etag}"'

    def test_does_not_modify_etag_if_already_set(self, app: CKANTestApp):
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

    def test_returns_304_if_etag_matches(self, app: CKANTestApp):
        """Test that response is changed to 304 Not Modified if ETag matches request."""
        request_headers = {}
        response: TestResponse = app.get('/', headers=request_headers)
        # use previous response ETag on next call
        assert response.headers["Etag"] is not None, response.headers

        request_headers["if_none_match"] = response.headers["Etag"]
        updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.status_code == 304, "original Etag was {}, second call etag was {}".format(
            response.headers["Etag"], updated_response.headers["Etag"])
        assert updated_response.get_data() == b""
        assert "Content-Length" not in updated_response.headers

    def test_does_not_return_304_if_etag_does_not_match(self, app: CKANTestApp):
        """Test that response is not modified if request's If-None-Match does not match the ETag."""

        request_headers = {}
        clean_response: TestResponse = app.get('/', headers=request_headers)
        clean_response_data = clean_response.get_data(as_text=True)
        request_headers: dict = {"if_none_match": "some-other-etag"}
        updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.status_code == 200, "should have received payload, not 304 as invalid etag was passed in"
        under_test_response_data = updated_response.get_data(as_text=True)
        assert clean_dynamic_values(clean_response_data) == clean_dynamic_values(under_test_response_data)
        assert updated_response.get_etag() == clean_response.get_etag(), "etag were not the same, got {}, original etag was {}".format(
            updated_response.get_etag(), clean_response.get_etag())

    def test_does_not_add_etag_if_streaming_response_encountered(self, app: CKANTestApp):
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

    def test_returns_200_if_etag_super_strong_set_in_g(self, app: CKANTestApp):
        with app.flask_app.app_context() as ctx:
            ctx.g.etag_super_strong = True
            response: TestResponse = app.get(
                url_for("index")
            )

        with app.flask_app.app_context() as ctx:
            ctx.g.etag_super_strong = True

            # use previous response ETag on next call
            assert response.headers["Etag"] is not None, response.headers
            request_headers = {"if_none_match": response.headers["Etag"]}
            updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.headers["ETag"] != response.headers["ETag"]
        assert updated_response.status_code == 200, "original Etag was {}, second call etag was {}".format(
            response.headers["Etag"], updated_response.headers["Etag"])
        assert updated_response.get_data() != response.get_data()

    def test_returns_200_if_etag_super_strong_when_logged_in(self, app: CKANTestApp):
        password = "RandomPassword123"
        user = factories.User(password=password)

        login_response: TestResponse = app.post(
            url_for("user.login"),
            data={
                "login": user["name"],
                "password": password
            },
        )

        assert login_response.headers["set-cookie"] is not None, login_response.headers

        match = re.search(r'ckan=([^;]+)', login_response.headers['set-cookie'])
        if match:
            cookie_value = match.group(0)  # Includes 'ckan=...' part
            headers = {"Cookie": cookie_value}
        else:
            pytest.fail("Not CKAN cookie found in Set-Cookie header")

        response: TestResponse = app.get(
            url_for("dashboard.index"),
            headers=headers
        )

        # use previous response ETag on next call
        assert response.headers["Etag"] is not None, response.headers

        headers["if_none_match"] = response.headers["Etag"]
        request_headers = {}
        updated_response: TestResponse = app.get('/', headers=request_headers)

        assert updated_response.headers["ETag"] != response.headers["ETag"]
        assert updated_response.status_code == 200, "original Etag was {}, second call etag was {}".format(
            response.headers["Etag"], updated_response.headers["Etag"])
        assert updated_response.get_data() != response.get_data()
