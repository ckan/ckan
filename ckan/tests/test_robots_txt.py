# encoding: utf-8
from ckan.lib.helpers import url_for


def test_robots_txt(app):
    url = url_for("home.robots_txt")
    res = app.get(url)
    assert res.status_code == 200
    assert res.headers.get(u"Content-Type") == u"text/plain; charset=utf-8"
    assert "User-agent" in res.body
