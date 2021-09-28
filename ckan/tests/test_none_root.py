# encoding: utf-8

import pytest

@pytest.mark.ckan_config(u"ckan.root_path", u"/data/{{LANG}}")
@pytest.mark.ckan_config(u"ckan.plugins", u"example_theme_v15_webassets")
@pytest.mark.usefixtures(u"with_plugins")
def test_resource_url(app):
    content = app.get(u"/").body
    if not "example_theme.css" in content:
        assert "example_theme.min.css" in content
    assert 'href="/data/webassets/example_theme' in content
