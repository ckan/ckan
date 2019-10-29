# encoding: utf-8


def test_robots_txt(app):
    response = app.get(u"/robots.txt", status=200)
    assert (
        response.headers.get(u"Content-Type") == u"text/plain; charset=utf-8"
    )
    assert u"User-agent" in response
