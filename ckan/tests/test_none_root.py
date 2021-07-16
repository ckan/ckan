# encoding: utf-8

import pytest
from ckan.tests.helpers import body_contains


@pytest.mark.ckan_config("ckan.root_path", "/data/{{LANG}}")
@pytest.mark.ckan_config("ckan.plugins", "example_theme_v15_webassets")
@pytest.mark.usefixtures("with_plugins")
def test_resource_url(app):
    content = app.get("/")
    if not body_contains(content, "example_theme.css"):
        assert body_contains(content, "example_theme.min.css")
    assert body_contains(content, 'href="/data/webassets/example_theme')
