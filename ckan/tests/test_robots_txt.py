# encoding: utf-8

from ckan.tests.helpers import body_contains


def test_robots_txt(app):
    res = app.get("/robots.txt")
    assert res.status_code == 200
    assert res.headers.get("Content-Type") == "text/plain; charset=utf-8"
    assert body_contains(res, "User-agent")
