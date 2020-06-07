# encoding: utf-8

import pytest
from ckan.tests.helpers import body_contains


@pytest.mark.ckan_config(u"ckan.root_path", u"/data/{{LANG}}")
@pytest.mark.ckan_config(u"ckan.plugins", u"example_theme_v15_fanstatic")
@pytest.mark.usefixtures(u"with_plugins")
def test_resource_url(app):
    content = app.get(u"/")
    if not body_contains(content, u"example_theme.css"):
        assert body_contains(content, u"example_theme.min.css")
    assert body_contains(content, u'href="/data/webassets/example_theme')
