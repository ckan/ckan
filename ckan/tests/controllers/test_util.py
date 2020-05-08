# encoding: utf-8

import pytest

from ckan.lib.helpers import url_for as url_for


@pytest.mark.usefixtures("with_request_context")
class TestUtil(object):
    def test_redirect_ok(self, app):
        response = app.get(
            url=url_for("util.internal_redirect"),
            query_string={"url": "/dataset"},
            status=302,
            follow_redirects=False,
        )
        assert (
            response.headers.get("Location") == "http://test.ckan.net/dataset"
        )

    def test_redirect_external(self, app):
        app.get(
            url=url_for("util.internal_redirect"),
            query_string={"url": "http://nastysite.com"},
            status=403,
        )

    @pytest.mark.parametrize("params", [{}, {"url": ""}])
    def test_redirect_no_params(self, params, app):
        app.get(
            url=url_for("util.internal_redirect"),
            query_string=params,
            status=400,
        )
