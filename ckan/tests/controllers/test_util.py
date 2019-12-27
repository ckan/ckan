# encoding: utf-8

import pytest

from ckan.lib.helpers import url_for as url_for


def test_redirect_ok(app):
    response = app.get(
        url=url_for("util.internal_redirect"),
        params={"url": "/dataset"},
        status=302,
    )
    assert response.headers.get("Location") == "http://test.ckan.net/dataset"


def test_redirect_external(app):
    app.get(
        url=url_for("util.internal_redirect"),
        params={"url": "http://nastysite.com"},
        status=403,
    )


@pytest.mark.parametrize("params", [{}, {"url": ""}])
def test_redirect_no_params(params, app):
    app.get(url=url_for("util.internal_redirect"), params=params, status=400)
