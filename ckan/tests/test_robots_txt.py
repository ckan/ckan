# encoding: utf-8


def test_robots_txt(app):
    res = app.get(u"/robots.txt")
    assert res.status_code == 200
    assert res.headers.get(u"Content-Type") == u"text/plain; charset=utf-8"
    assert "User-agent" in res.body
