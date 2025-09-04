import os
import re

import pytest

from ckan.common import g

from ckan.lib.webassets_tools import render_assets, create_library, include_asset


def _remove_cache_busting(tag: str) -> str:

    return re.sub(r'\?[^"]*', "", tag)


@pytest.fixture
def test_assets(app):

    with app.flask_app.app_context():
        current_assets = getattr(g, "_webassets", None)
        assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))

        create_library("tests", assets_path)

        yield
        g._webassets = current_assets


# def test_render_assets(test_assets, name, rendered_tag)


@pytest.mark.parametrize(
    "type_,name,expected",
    [
        (
            "script",
            "tests/test_js_basic",
            '<script src="/webassets/test/rendered_test.js" type="text/javascript"></script>',
        ),
        (
            "style",
            "tests/test_css_basic",
            '<link href="/webassets/test/rendered_test.css" rel="stylesheet"/>',
        ),
        (
            "script",
            "tests/test_js_attr_key",
            '<script src="/webassets/test/rendered_test.js" defer type="text/javascript"></script>',
        ),
        (
            "script",
            "tests/test_js_attr_key_value",
            '<script src="/webassets/test/rendered_test.js" crossorigin="anonymous" type="text/javascript"></script>',
        ),
        (
            "script",
            "tests/test_js_attr_both",
            '<script src="/webassets/test/rendered_test.js" async crossorigin="anonymous" type="text/javascript"></script>',
        ),
        (
            "style",
            "tests/test_css_attr_key_value",
            '<link href="/webassets/test/rendered_test.css" fetchpriority="high" rel="stylesheet"/>',
        ),
        (
            "script",
            "tests/test_js_attr_preload",
            '<link href="/webassets/test/rendered_test.js" rel="preload" as="script"/>',
        ),

    ],
)
def test_render_assets(test_assets, type_, name, expected):

    include_asset(name)

    assert _remove_cache_busting(render_assets(type_)) == expected
