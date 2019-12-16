# encoding: utf-8


def test_without_redirect(app):
    # this is what a web bot might do
    res = app.get("/error/document")
    assert "There is no error." in str(res)
