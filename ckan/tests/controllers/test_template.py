# encoding: utf-8

import pytest


@pytest.mark.parametrize(
    u"url,expected",
    [
        (u"/robots.txt", u"text/plain; charset=utf-8"),
        (u"/page", u"text/html; charset=utf-8"),
        (u"/page.html", u"text/html; charset=utf-8"),
    ],
)
def test_content_type(url, expected, app):
    response = app.get(url, status=200)
    assert response.headers.get(u"Content-Type") == expected
