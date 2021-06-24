# encoding: utf-8

import datetime
import hashlib
import six
import os

import pytz
import tzlocal
from babel import Locale
from six import text_type
import pytest

import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.exceptions
from ckan.tests import helpers, factories
import ckan.lib.base as base


CkanUrlException = ckan.exceptions.CkanUrlException


class BaseUrlFor(object):
    @pytest.fixture(autouse=True)
    def request_context(self, monkeypatch, ckan_config, app):
        monkeypatch.setitem(ckan_config, "ckan.site_url", "http://example.com")
        self.request_context = app.flask_app.test_request_context()
        self.request_context.push()
        yield
        self.request_context.pop()


class TestHelpersUrlForStatic(BaseUrlFor):
    def test_url_for_static(self):
        url = "/assets/ckan.jpg"
        assert h.url_for_static(url) == url

    def test_url_for_static_adds_starting_slash_if_url_doesnt_have_it(self):
        slashless_url = "ckan.jpg"
        url = "/" + slashless_url
        assert h.url_for_static(slashless_url) == url

    def test_url_for_static_converts_unicode_strings_to_regular_strings(self):
        url = u"/ckan.jpg"
        assert isinstance(h.url_for_static(url), str)

    def test_url_for_static_raises_when_called_with_external_urls(self):
        url = "http://assets.ckan.org/ckan.jpg"
        with pytest.raises(CkanUrlException):
            h.url_for_static(url)

    def test_url_for_static_raises_when_called_with_protocol_relative(self):
        url = "//assets.ckan.org/ckan.jpg"
        with pytest.raises(CkanUrlException):
            h.url_for_static(url)

    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_static_with_root_path(self):
        url = "/my/custom/path/foo/my-asset/file.txt"
        generated_url = h.url_for_static("/my-asset/file.txt")
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_static_qualified_with_root_path(self):
        url = "http://example.com/my/custom/path/foo/my-asset/file.txt"
        generated_url = h.url_for_static("/my-asset/file.txt", qualified=True)
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.site_url", "http://example.com")
    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_static_with_root_path_and_script_name_env(self, monkeypatch):
        monkeypatch.setitem(os.environ, "SCRIPT_NAME", "/my/custom/path")
        url = "http://example.com/my/custom/path/foo/my-asset/file.txt"
        generated_url = h.url_for_static("/my-asset/file.txt", qualified=True)
        assert generated_url == url


@pytest.mark.parametrize(
    "url",
    [
        "/assets/ckan.jpg",
        "http://assets.ckan.org/ckan.jpg",
        u"/ckan.jpg",
        "/ckan.jpg",
        "//assets.ckan.org/ckan.jpg",
    ],
)
def test_url_for_static_or_external(url):
    generated = h.url_for_static_or_external(url)
    assert generated == url
    assert isinstance(generated, str)


class TestHelpersUrlFor(BaseUrlFor):
    @pytest.mark.parametrize(
        "extra,exp",
        [
            ({}, "/dataset/my_dataset"),
            ({"locale": "de"}, "/de/dataset/my_dataset"),
            ({"qualified": False}, "/dataset/my_dataset"),
            ({"qualified": True}, "http://example.com/dataset/my_dataset"),
            (
                {"qualified": True, "locale": "de"},
                "http://example.com/de/dataset/my_dataset",
            ),
        ],
    )
    def test_url_for_default(self, extra, exp):
        generated_url = h.url_for("dataset.read", id="my_dataset", **extra)
        assert generated_url == exp

    @pytest.mark.ckan_config("ckan.root_path", "/foo/{{LANG}}")
    def test_url_for_with_locale_object(self):
        url = "/foo/de/dataset/my_dataset"
        generated_url = h.url_for("/dataset/my_dataset", locale=Locale("de"))
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/my/prefix")
    def test_url_for_qualified_with_root_path(self):
        url = "http://example.com/my/prefix/dataset/my_dataset"
        generated_url = h.url_for(
            "dataset.read", id="my_dataset", qualified=True
        )
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_qualified_with_root_path_and_locale(self):
        url = "http://example.com/my/custom/path/de/foo/dataset/my_dataset"
        generated_url = h.url_for(
            "dataset.read", id="my_dataset", qualified=True, locale="de"
        )
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.site_url", "http://example.com")
    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_qualified_with_root_path_locale_and_script_name_env(self, monkeypatch):
        monkeypatch.setitem(os.environ, "SCRIPT_NAME", "/my/custom/path")
        url = "http://example.com/my/custom/path/de/foo/dataset/my_dataset"
        generated_url = h.url_for(
            "dataset.read", id="my_dataset", qualified=True, locale="de"
        )
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.site_url", "http://example.com")
    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path/{{LANG}}/foo")
    def test_url_for_with_root_path_locale_and_script_name_env(self, monkeypatch):
        monkeypatch.setitem(os.environ, "SCRIPT_NAME", "/my/custom/path")

        url = "/my/custom/path/de/foo/dataset/my_dataset"
        generated_url = h.url_for("dataset.read", id="my_dataset", locale="de")
        assert generated_url == url

    @pytest.mark.ckan_config("debug", True)
    @pytest.mark.ckan_config("DEBUG", True)  # Flask's internal debug flag
    @pytest.mark.ckan_config("ckan.root_path", "/my/custom/path")
    def test_debugtoolbar_url(self, ckan_config):
        # test against built-in `url_for`, that is used by debugtoolbar ext.
        from flask import url_for
        expected = "/my/custom/path/_debug_toolbar/static/test.js"
        url = url_for('_debug_toolbar.static', filename='test.js')
        assert url == expected


class TestHelpersUrlForFlaskandPylons(BaseUrlFor):
    def test_url_for_flask_route_new_syntax(self):
        url = "/api/3"
        generated_url = h.url_for("api.get_api", ver=3)
        assert generated_url == url

    def test_url_for_flask_route_old_syntax(self):
        url = "/api/3"
        generated_url = h.url_for(controller="api", action="get_api", ver=3)
        assert generated_url == url

    def test_url_for_flask_route_new_syntax_external(self):
        url = "http://example.com/api/3"
        generated_url = h.url_for("api.get_api", ver=3, _external=True)
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/{{LANG}}/data")
    def test_url_for_flask_route_new_syntax_external_with_root_path(self):
        url = "http://example.com/data/api/3"
        generated_url = h.url_for("api.get_api", ver=3, _external=True)
        assert generated_url == url

    def test_url_for_flask_route_old_syntax_external(self):
        url = "http://example.com/api/3"
        generated_url = h.url_for(
            controller="api", action="get_api", ver=3, _external=True
        )
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/{{LANG}}/data")
    def test_url_for_flask_route_old_syntax_external_with_root_path(self):
        url = "http://example.com/data/api/3"
        generated_url = h.url_for(
            controller="api", action="get_api", ver=3, _external=True
        )
        assert generated_url == url

    def test_url_for_flask_route_old_syntax_qualified(self):
        url = "http://example.com/api/3"
        generated_url = h.url_for(
            controller="api", action="get_api", ver=3, qualified=True
        )
        assert generated_url == url

    @pytest.mark.ckan_config("ckan.root_path", "/{{LANG}}/data")
    def test_url_for_flask_route_old_syntax_qualified_with_root_path(self):
        url = "http://example.com/data/api/3"
        generated_url = h.url_for(
            controller="api", action="get_api", ver=3, qualified=True
        )
        assert generated_url == url

    def test_url_for_flask_route_new_syntax_site_url(self):
        url = "/api/3"
        generated_url = h.url_for("api.get_api", ver=3)
        assert generated_url == url

    def test_url_for_flask_route_old_syntax_site_url(self):
        url = "/api/3"
        generated_url = h.url_for(controller="api", action="get_api", ver=3)
        assert generated_url == url

    def test_url_for_flask_route_new_syntax_request_context(self, app):
        with app.flask_app.test_request_context():
            url = "/api/3"
            generated_url = h.url_for("api.get_api", ver=3)
            assert generated_url == url


class TestHelpersRenderMarkdown(object):
    @pytest.mark.parametrize(
        "data,output,allow_html",
        [
            ("<h1>moo</h1>", "<h1>moo</h1>", True),
            ("<h1>moo</h1>", "<p>moo</p>", False),
            (
                "http://example.com",
                '<p><a href="http://example.com" target="_blank" rel="nofollow">http://example.com</a></p>',
                False,
            ),
            (
                "https://example.com/page.html",
                '<p><a href="https://example.com/page.html" target="_blank" rel="nofollow">https://example.com/page.html</a></p>',
                False,
            ),
            (
                "My link: http://example.com/page.html.",
                '<p>My link: <a href="http://example.com/page.html" target="_blank" rel="nofollow">http://example.com/page.html</a>.</p>',
                False,
            ),
            (
                u"* [Foo (http://foo.bar) * Bar] (http://foo.bar)",
                u'<ul>\n<li>[Foo (<a href="http://foo.bar" target="_blank" rel="nofollow">http://foo.bar</a>) * Bar] (<a href="http://foo.bar" target="_blank" rel="nofollow">http://foo.bar</a>)</li>\n</ul>',
                False,
            ),
            (u"[text](javascript: alert(1))", u"<p><a>text</a></p>", False),
            (
                u'<p onclick="some.script"><img onmouseover="some.script" src="image.png" /> and text</p>',
                u"<p>and text</p>",
                False,
            ),
            (u"#heading", u"<h1>heading</h1>", False),
            (u"##heading", u"<h2>heading</h2>", False),
            (u"###heading", u"<h3>heading</h3>", False),
            (
                u"![image](/image.png)",
                u'<p><img alt="image" src="/image.png"></p>',
                False,
            ),
            (
                u"Something **important**",
                u"<p>Something <strong>important</strong></p>",
                False,
            ),
            (
                u"Something *important*",
                u"<p>Something <em>important</em></p>",
                False,
            ),
            (
                u"[link](/url?a=1&b=2)",
                u'<p><a href="/url?a=1&amp;b=2">link</a></p>',
                False,
            ),
            (
                u"http://example.com/page?a=1&b=2",
                u'<p><a href="http://example.com/page?a=1&amp;b=2" target="_blank" rel="nofollow">http://example.com/page?a=1&amp;b=2</a></p>',
                False,
            ),
            (
                "tag:test-tag foobar",
                (
                    '<p><a href="/dataset/?tags=test-tag">tag:test-tag</a> foobar</p>'
                ),
                False,
            ),
            (
                'tag:"test-tag" foobar',
                '<p><a href="/dataset/?tags=test-tag">tag:&quot;test-tag&quot;</a> foobar</p>',
                False,
            ),
            (
                'tag:"test tag" foobar',
                '<p><a href="/dataset/?tags=test+tag">tag:&quot;test tag&quot;</a> foobar</p>',
                False,
            ),
            (
                'tag:test tag" foobar',  # should match 'tag:test'
                (
                    '<p><a href="/dataset/?tags=test">tag:test</a> tag" foobar</p>'
                ),
                False,
            ),
            (
                'tag:test" foobar',  # should match 'tag:test'
                '<p><a href="/dataset/?tags=test">tag:test</a>" foobar</p>',
                False,
            ),
            (
                'tag:"Test- _." foobar',
                '<p><a href="/dataset/?tags=Test-+_.">tag:&quot;Test- _.&quot;</a> foobar</p>',
                False,
            ),
            (
                "tag:Test,tag foobar",
                '<p><a href="/dataset/?tags=Test">tag:Test</a>,tag foobar</p>',
                False,
            ),
            (
                u'tag:"Japanese katakana \u30a1" blah',
                u'<p><a href="/dataset/?tags=Japanese+katakana+%E3%82%A1">tag:&quot;Japanese katakana \u30a1&quot;</a> blah</p>',
                False,
            ),
            (
                "http://somelink/",
                '<p><a href="http://somelink/" target="_blank" rel="nofollow">http://somelink/</a></p>',
                False,
            ),
            (
                "http://somelink.com/#anchor",
                '<p><a href="http://somelink.com/#anchor" target="_blank" rel="nofollow">http://somelink.com/#anchor</a></p>',
                False,
            ),
            (
                "http://somelink.com",
                '<p><a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a></p>',
                False,
            ),
            (
                "go to http://somelink.com",
                '<p>go to <a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a></p>',
                False,
            ),
            (
                u"<a href=\u201dsomelink\u201d>somelink</a>",
                "<p>somelink</p>",
                False,
            ),
        ],
    )
    def test_render_markdown(self, data, output, allow_html):
        assert h.render_markdown(data, allow_html=allow_html) == output

    def test_internal_tag_with_no_closing_quote_does_not_match(self):
        """Asserts that without an opening quote only one word is matched"""
        data = 'tag:"test tag foobar'
        out = h.render_markdown(data)
        assert "<a href" not in out

    def test_tag_names_match_simple_punctuation(self):
        """Asserts punctuation and capital letters are matched in the tag name"""
        data = 'tag:"Test- _." foobar'
        output = '<p><a href="/dataset/?tags=Test-+_.">tag:&quot;Test- _.&quot;</a> foobar</p>'
        assert h.render_markdown(data) == output

    def test_tag_names_do_not_match_commas(self):
        """Asserts commas don't get matched as part of a tag name"""
        data = "tag:Test,tag foobar"
        output = '<p><a href="/dataset/?tags=Test">tag:Test</a>,tag foobar</p>'
        assert h.render_markdown(data) == output

    def test_tag_names_dont_match_non_space_whitespace(self):
        """Asserts that the only piece of whitespace matched in a tagname is a space"""
        whitespace_characters = "\t\n\r\f\v"
        for ch in whitespace_characters:
            data = "tag:Bad" + ch + "space"
            output = '<p><a href="/dataset/?tags=Bad">tag:Bad</a>'
            result = h.render_markdown(data)
            assert output in result, "\nGot: %s\nWanted: %s" % (result, output)


class TestHelpersRemoveLineBreaks(object):
    def test_remove_linebreaks_removes_linebreaks(self):
        test_string = "foo\nbar\nbaz"
        result = h.remove_linebreaks(test_string)

        assert (
            result.find("\n") == -1
        ), '"remove_linebreaks" should remove line breaks'

    def test_remove_linebreaks_casts_into_unicode(self):
        class UnicodeLike(text_type):
            pass

        test_string = UnicodeLike("foo")
        result = h.remove_linebreaks(test_string)

        strType = u"".__class__
        assert (
            result.__class__ == strType
        ), '"remove_linebreaks" casts into unicode()'


class TestLicenseOptions(object):
    def test_includes_existing_license(self):
        licenses = h.license_options("some-old-license")
        assert dict(licenses)["some-old-license"] == "some-old-license"
        # and it is first on the list
        assert licenses[0][0] == "some-old-license"


@pytest.mark.parametrize(
    "fmt,exp",
    [
        ("xls", "XLS"),
        ("Excel document", "XLS"),
        ("application/vnd.ms-excel", "XLS"),
        ("application/msexcel", "XLS"),
        ("Excel", "XLS"),
        ("tsv", "TSV"),
        ("text/tab-separated-values", "TSV"),
        ("text/tsv", "TSV"),
    ],
)
def test_unified_resource_format(fmt, exp):
    assert h.unified_resource_format(fmt) == exp


class TestGetDisplayTimezone(object):
    @pytest.mark.ckan_config("ckan.display_timezone", "")
    def test_missing_config(self):
        assert h.get_display_timezone() == pytz.timezone("utc")

    @pytest.mark.ckan_config("ckan.display_timezone", "server")
    def test_server_timezone(self):
        assert h.get_display_timezone() == tzlocal.get_localzone()

    @pytest.mark.ckan_config("ckan.display_timezone", "America/New_York")
    def test_named_timezone(self):
        assert h.get_display_timezone() == pytz.timezone("America/New_York")


@pytest.mark.parametrize(
    "date,extra,exp",
    [
        (
            datetime.datetime(2008, 4, 13, 20, 40, 59, 123456),
            {},
            "April 13, 2008",
        ),
        (
            datetime.datetime(2008, 4, 13, 20, 40, 59, 123456),
            {"with_hours": True},
            "April 13, 2008, 20:40 (UTC)",
        ),
        (
            datetime.datetime(2008, 4, 13, 20, 40, 59, 123456),
            {"with_seconds": True},
            "April 13, 2008 at 8:40:59 PM UTC",
        ),
        ("2008-04-13T20:40:20.123456", {}, "April 13, 2008"),
        (None, {}, ""),
        ("1875-04-13T20:40:20.123456", {"date_format": "%Y"}, "1875"),
        ("1875-04-13T20:40:20.123456", {"date_format": "%y"}, "75"),
        ("2008-04-13T20:40:20.123456", {"date_format": "%%%Y"}, "%2008"),
    ],
)
@pytest.mark.usefixtures("with_request_context")
def test_render_datetime(date, extra, exp):
    assert h.render_datetime(date, **extra) == exp


@pytest.mark.usefixtures("with_request_context")
@pytest.mark.freeze_time("2020-02-17 12:00:00")
@pytest.mark.parametrize(
    "date, exp",
    [
        (
            datetime.datetime(2020, 2, 17, 11, 59, 30),
            "30 seconds ago",
        ),
        (
            datetime.datetime(2020, 2, 17, 11, 59, 0),
            "1 minute ago",
        ),
        (
            datetime.datetime(2020, 2, 17, 11, 55, 0),
            "5 minutes ago",
        ),
        (
            datetime.datetime(2020, 2, 17, 11, 0, 0),
            "1 hour ago",
        ),
        (
            datetime.datetime(2020, 2, 17, 7, 0, 0),
            "5 hours ago",
        ),
        (
            datetime.datetime(2020, 2, 16, 12, 0, 0),
            "1 day ago",
        ),
        (
            datetime.datetime(2020, 2, 12, 12, 0, 0),
            "5 days ago",
        ),
        (
            datetime.datetime(2020, 1, 17, 12, 0, 0),
            "1 month ago",
        ),
        (
            datetime.datetime(2019, 9, 17, 12, 0, 0),
            "5 months ago",
        ),
        (
            datetime.datetime(2019, 1, 17, 12, 0, 0),
            "1 year ago",
        ),
        (
            datetime.datetime(2015, 1, 17, 12, 0, 0),
            "5 years ago",
        ),
    ]
)
def test_time_ago_from_timestamp(date, exp):
    assert h.time_ago_from_timestamp(date) == exp


def test_clean_html_disallowed_tag():
    assert h.clean_html("<b><bad-tag>Hello") == u"<b>&lt;bad-tag&gt;Hello</b>"


def test_clean_html_non_string():
    # allow a datetime for compatibility with older ckanext-datapusher
    assert (
        h.clean_html(datetime.datetime(2018, 1, 5, 10, 48, 23, 463511))
        == u"2018-01-05 10:48:23.463511"
    )


@pytest.mark.usefixtures("with_request_context")
class TestBuildNavMain(object):
    def test_flask_routes(self):
        menu = (
            ("home.index", "Home"),
            ("dataset.search", "Datasets"),
            ("organization.index", "Organizations"),
            ("group.index", "Groups"),
            ("home.about", "About"),
        )
        assert h.build_nav_main(*menu) == (
            '<li class="active"><a href="/">Home</a></li>'
            '<li><a href="/dataset/">Datasets</a></li>'
            '<li><a href="/organization/">Organizations</a></li>'
            '<li><a href="/group/">Groups</a></li>'
            '<li><a href="/about">About</a></li>'
        )

    def test_active_in_flask_routes(self, test_request_context):
        with test_request_context(u'/organization'):
            menu = (
                ("home.index", "Home"),
                ("dataset.search", "Datasets", ['dataset', 'resource']),
                ("organization.index", "Organizations"),
                ("group.index", "Groups"),
                ("home.about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li><a href="/dataset/">Datasets</a></li>'
                '<li class="active"><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

    @pytest.mark.usefixtures("clean_db")
    def test_active_in_resource_controller(self, test_request_context):

        dataset = factories.Dataset()
        with test_request_context(u'/dataset/' + dataset['id']):
            menu = (
                ("home.index", "Home"),
                ("dataset.search", "Datasets", ['dataset', 'resource']),
                ("organization.index", "Organizations"),
                ("group.index", "Groups"),
                ("home.about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li class="active"><a href="/dataset/">Datasets</a></li>'
                '<li><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

        resource = factories.Resource(name="some_resource")
        with test_request_context(u'/dataset/' + resource['package_id'] + '/resource/' + resource['id']):
            menu = (
                ("home.index", "Home"),
                ("dataset.search", "Datasets", ['dataset', 'resource']),
                ("organization.index", "Organizations"),
                ("group.index", "Groups"),
                ("home.about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li class="active"><a href="/dataset/">Datasets</a></li>'
                '<li><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

    def test_legacy_pylon_routes(self):
        menu = (
            ("home", "Home"),
            ("search", "Datasets"),
            ("organizations_index", "Organizations"),
            ("group_index", "Groups"),
            ("about", "About"),
        )
        assert h.build_nav_main(*menu) == (
            '<li class="active"><a href="/">Home</a></li>'
            '<li><a href="/dataset/">Datasets</a></li>'
            '<li><a href="/organization/">Organizations</a></li>'
            '<li><a href="/group/">Groups</a></li>'
            '<li><a href="/about">About</a></li>'
        )

    def test_active_in_legacy_pylon_routes(self, test_request_context):

        with test_request_context(u'/organization'):
            menu = (
                ("home", "Home"),
                ("search", "Datasets", ['dataset', 'resource']),
                ("organizations_index", "Organizations"),
                ("group_index", "Groups"),
                ("about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li><a href="/dataset/">Datasets</a></li>'
                '<li class="active"><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

    @pytest.mark.usefixtures("clean_db")
    def test_active_in_resource_controller_legacy_pylon_routes(self, test_request_context):

        dataset = factories.Dataset()
        with test_request_context(u'/dataset/' + dataset['id']):
            menu = (
                ("home", "Home"),
                ("search", "Datasets", ['dataset', 'resource']),
                ("organizations_index", "Organizations"),
                ("group_index", "Groups"),
                ("about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li class="active"><a href="/dataset/">Datasets</a></li>'
                '<li><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

        resource = factories.Resource(name="some_resource")
        with test_request_context(u'/dataset/' + resource['package_id'] + '/resource/' + resource['id']):
            menu = (
                ("home", "Home"),
                ("search", "Datasets", ['dataset', 'resource']),
                ("organizations_index", "Organizations"),
                ("group_index", "Groups"),
                ("about", "About"),
            )
            assert h.build_nav_main(*menu) == (
                '<li><a href="/">Home</a></li>'
                '<li class="active"><a href="/dataset/">Datasets</a></li>'
                '<li><a href="/organization/">Organizations</a></li>'
                '<li><a href="/group/">Groups</a></li>'
                '<li><a href="/about">About</a></li>'
            )

    def test_dataset_navigation_legacy_routes(self):
        dataset_name = "test-dataset"
        assert (
            h.build_nav_icon("dataset_read", "Datasets", id=dataset_name)
            == '<li><a href="/dataset/test-dataset">Datasets</a></li>'
        )
        assert (
            h.build_nav_icon("dataset_groups", "Groups", id=dataset_name)
            == '<li><a href="/dataset/groups/test-dataset">Groups</a></li>'
        )
        assert (
            h.build_nav_icon(
                "dataset_activity", "Activity Stream", id=dataset_name
            )
            == '<li><a href="/dataset/activity/test-dataset">Activity Stream</a></li>'
        )

    def test_group_navigation_legacy_routes(self):
        group_name = "test-group"
        assert (
            h.build_nav_icon("group_read", "Datasets", id=group_name)
            == '<li><a href="/group/test-group">Datasets</a></li>'
        )
        assert (
            h.build_nav_icon(
                "group_activity", "Activity Stream", id=group_name
            )
            == '<li><a href="/group/activity/test-group">Activity Stream</a></li>'
        )
        assert (
            h.build_nav_icon("group_about", "About", id=group_name)
            == '<li><a href="/group/about/test-group">About</a></li>'
        )

    def test_organization_navigation_legacy_routes(self):
        org_name = "test-org"
        assert (
            h.build_nav_icon("organization_read", "Datasets", id=org_name)
            == '<li><a href="/organization/test-org">Datasets</a></li>'
        )
        assert (
            h.build_nav_icon(
                "organization_activity", "Activity Stream", id=org_name
            )
            == '<li><a href="/organization/activity/test-org">Activity Stream</a></li>'
        )
        assert (
            h.build_nav_icon("organization_about", "About", id=org_name)
            == '<li><a href="/organization/about/test-org">About</a></li>'
        )


class HelpersTestPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes, inherit=True)

    controller = "ckan.tests.lib.test_helpers:TestHelperController"

    def after_map(self, _map):

        _map.connect(
            "/broken_helper_as_attribute",
            controller=self.controller,
            action="broken_helper_as_attribute",
        )

        _map.connect(
            "/broken_helper_as_item",
            controller=self.controller,
            action="broken_helper_as_item",
        )

        _map.connect(
            "/helper_as_attribute",
            controller=self.controller,
            action="helper_as_attribute",
        )

        _map.connect(
            "/helper_as_item",
            controller=self.controller,
            action="helper_as_item",
        )

        return _map


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestActivityListSelect(object):
    def test_simple(self):
        pkg_activity = {
            "id": "id1",
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = h.activity_list_select([pkg_activity], "")

        html = out[0]
        assert (
            str(html)
            == '<option value="id1" >February 1, 2018 at 10:58:59 AM UTC'
            "</option>"
        )
        assert hasattr(html, "__html__")  # shows it is safe Markup

    def test_selected(self):
        pkg_activity = {
            "id": "id1",
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = h.activity_list_select([pkg_activity], "id1")

        html = out[0]
        assert (
            str(html)
            == '<option value="id1" selected>February 1, 2018 at 10:58:59 AM UTC'
            "</option>"
        )
        assert hasattr(html, "__html__")  # shows it is safe Markup

    def test_escaping(self):
        pkg_activity = {
            "id": '">',  # hacked somehow
            "timestamp": datetime.datetime(2018, 2, 1, 10, 58, 59),
        }

        out = h.activity_list_select([pkg_activity], "")

        html = out[0]
        assert str(html).startswith(u'<option value="&#34;&gt;" >')


class TestAddUrlParam(object):

    @pytest.mark.parametrize(u'url,params,expected', [
        (u'/dataset', {u'a': u'2'}, u'/dataset/?a=2'),
        (u'/dataset?a=1', {u'a': u'2'}, u'/dataset/?a=1&a=2'),
        (u'/dataset?a=1&a=3', {u'a': u'2'}, u'/dataset/?a=1&a=3&a=2'),
        (u'/dataset?a=2', {u'a': u'2'}, u'/dataset/?a=2&a=2'),
    ])
    def test_new_param(self, test_request_context, url, params, expected):
        with test_request_context(url):
            assert h.add_url_param(new_params=params) == expected

    def test_alternative_url(self, test_request_context):
        with test_request_context(u'/dataset'):
            assert h.add_url_param(u'/group') == u'/group'
            assert h.add_url_param(
                u'/group', new_params={'x': 'y'}) == u'/group?x=y'
            assert h.add_url_param() == u'/dataset/'

    @pytest.mark.parametrize(u'controller,action,extras', [
        ('dataset', 'read', {'id': 'uuid'}),
        ('dataset', 'search', {'q': '*:*'}),
        ('organization', 'index', {}),
        ('home', 'index', {'a': '1'}),
        ('dashboard', 'index', {}),
    ])
    def test_controller_action(
            self, test_request_context, controller, action, extras):
        with test_request_context(u'/dataset/'):
            assert h.add_url_param(
                controller=controller, action=action, extras=extras
            ) == h.url_for(controller + '.' + action, **extras)


def test_sanitize_url():
    assert h.sanitize_url(
        u'http://example.com/some-path/to_a/file.jpg'
    ) == u'http://example.com/some-path/to_a/file.jpg'
    assert h.sanitize_url(
        u'sh+eme://[net:loc]:12345/a/path?a=b&c=d'
    ) == u'sh+eme://[net:loc]:12345/a/path?a=b&c=d'
    assert h.sanitize_url(
        u'http://éxàmple.com/some:path/to+a/fil[e].jpg'
    ) == u'http://éxàmple.com/some%3Apath/to%2Ba/fil%5Be%5D.jpg'
    assert h.sanitize_url('http://bad host/path') == ''
    assert h.sanitize_url(
        u'http://x/things" onerror=alert(document.domain)>'
    ) == u'http://x/things%22%20onerror%3Dalert%28document.domain%29%3E'
    assert h.sanitize_url(
        h.sanitize_url(
            u'http://éxàmple.com/some:path/to+a/fil[e].jpg'
        )
    ) == h.sanitize_url(u'http://éxàmple.com/some:path/to+a/fil[e].jpg')


def test_extract_markdown():
    WITH_HTML = u"""Data exposed: &mdash;
Size of dump and data set: size?
Notes: this is the classic RDF source but historically has had some problems with RDF correctness.
"""

    WITH_UNICODE = u"""[From the project website] This project collects information on China’s foreign aid from the China Commerce Yearbook (中国商务年鉴) and the Almanac of China’s Foreign Economic Relations & Trade (中国对外经济贸易年间), published annually by China’s Ministry of Commerce (MOFCOM). Data is reported for each year between 1990 and 2005, with the exception of 2002, in which year China’s Ministry of Commerce published no project-level data on its foreign aid giving."""

    assert "Data exposed" in h.markdown_extract(WITH_HTML)
    assert "collects information" in h.markdown_extract(WITH_UNICODE)


@pytest.mark.parametrize("string, date", [
    ("2008-04-13", datetime.datetime(2008, 4, 13)),
    ("2008-04-13T20:40:20.123456", datetime.datetime(2008, 4, 13, 20, 40, 20, 123456)),
    ("2008-04-13T20:40:20", datetime.datetime(2008, 4, 13, 20, 40, 20)),
    ("2008-04-13T20:40:20.1234", datetime.datetime(2008, 4, 13, 20, 40, 20, 123400)),
])
def test_date_str_to_datetime_valid(string, date):
    assert h.date_str_to_datetime(string) == date


@pytest.mark.parametrize("string", [
    "2008-04-13T20:40:20-01:30",
    "2008-04-13T20:40:20-0130",
    "2008-04-13T20:40:20foobar",
])
def test_date_str_to_datetime_invalid(string):
    with pytest.raises(ValueError):
        h.date_str_to_datetime(string)


def test_gravatar():
    email = "zephod@gmail.com"
    expected = '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=mm"'

    email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
    res = h.gravatar(email_hash, 200, default="mm")
    assert expected in res


def test_gravatar_config_set_default(ckan_config):
    """Test when default gravatar is None, it is pulled from the config file"""
    email = "zephod@gmail.com"
    default = ckan_config.get("ckan.gravatar_default", "identicon")
    expected = (
        '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=%s"'
        % default
    )
    email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
    res = h.gravatar(email_hash, 200)
    assert expected in res


def test_gravatar_encodes_url_correctly():
    """Test when the default gravatar is a url, it gets urlencoded"""
    email = "zephod@gmail.com"
    default = "http://example.com/images/avatar.jpg"
    expected = '<img src="//gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=http%3A%2F%2Fexample.com%2Fimages%2Favatar.jpg"'

    email_hash = hashlib.md5(six.ensure_binary(email)).hexdigest()
    res = h.gravatar(email_hash, 200, default=default)
    assert expected in res


def test_parse_rfc_2822_no_timezone_specified():
    """
    Parse "Tue, 15 Nov 1994 12:45:26" successfully.

    Assuming it's UTC.
    """
    dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26")
    assert dt.isoformat() == "1994-11-15T12:45:26+00:00"


def test_parse_rfc_2822_gmt_case():
    """
    Parse "Tue, 15 Nov 1994 12:45:26 GMT" successfully.

    GMT obs-zone specified
    """
    dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26 GMT")
    assert dt.isoformat() == "1994-11-15T12:45:26+00:00"


def test_parse_rfc_2822_with_offset():
    """
    Parse "Tue, 15 Nov 1994 12:45:26 +0700" successfully.
    """
    dt = h.parse_rfc_2822_date("Tue, 15 Nov 1994 12:45:26 +0700")
    assert dt.isoformat() == "1994-11-15T12:45:26+07:00"


def test_escape_js():
    input_str = '{"type":"point", "desc":"Bla bla O\'hara.\\nNew line."}'
    expected_str = '{\\"type\\":\\"point\\", \\"desc\\":\\"Bla bla O\\\'hara.\\\\nNew line.\\"}'
    output_str = h.escape_js(input_str)
    assert output_str == expected_str


@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_get_pkg_dict_extra():

    from ckan.lib.create_test_data import CreateTestData
    from ckan import model
    from ckan.logic import get_action

    CreateTestData.create()

    pkg_dict = helpers.call_action("package_show", id="annakarenina")

    assert h.get_pkg_dict_extra(pkg_dict, "genre") == "romantic novel"

    assert h.get_pkg_dict_extra(pkg_dict, "extra_not_found") is None

    assert (
        h.get_pkg_dict_extra(pkg_dict, "extra_not_found", "default_value")
        == "default_value"
    )

    model.repo.rebuild_db()
