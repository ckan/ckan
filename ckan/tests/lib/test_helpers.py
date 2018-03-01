# encoding: utf-8

import datetime

import nose
import pytz
import tzlocal
from babel import Locale
from six import text_type

from ckan.common import config
import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.exceptions
from ckan.tests import helpers
import ckan.lib.base as base

ok_ = nose.tools.ok_
eq_ = nose.tools.eq_
raises = nose.tools.raises
CkanUrlException = ckan.exceptions.CkanUrlException


class BaseUrlFor(object):

    @classmethod
    def setup_class(cls):

        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls._original_config = dict(config)
        config['ckan.site_url'] = 'http://example.com'
        cls.app = helpers._get_test_app()

    def setup(self):

        self.request_context = self.app.flask_app.test_request_context()
        self.request_context.push()

    def teardown(self):

        self.request_context.pop()

    @classmethod
    def teardown_class(cls):
        # Restore the config to its original values
        config.clear()
        config.update(cls._original_config)


class TestHelpersUrlForStatic(BaseUrlFor):

    def test_url_for_static(self):
        url = '/assets/ckan.jpg'
        eq_(h.url_for_static(url), url)

    def test_url_for_static_adds_starting_slash_if_url_doesnt_have_it(self):
        slashless_url = 'ckan.jpg'
        url = '/' + slashless_url
        eq_(h.url_for_static(slashless_url), url)

    def test_url_for_static_converts_unicode_strings_to_regular_strings(self):
        url = u'/ckan.jpg'
        assert isinstance(h.url_for_static(url), str)

    def test_url_for_static_raises_when_called_with_external_urls(self):
        url = 'http://assets.ckan.org/ckan.jpg'
        nose.tools.assert_raises(CkanUrlException, h.url_for_static, url)

    def test_url_for_static_raises_when_called_with_protocol_relative(self):
        url = '//assets.ckan.org/ckan.jpg'
        nose.tools.assert_raises(CkanUrlException, h.url_for_static, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_static_with_root_path(self):
        url = '/my/custom/path/foo/my-asset/file.txt'
        generated_url = h.url_for_static('/my-asset/file.txt')
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_static_qualified_with_root_path(self):
        url = 'http://example.com/my/custom/path/foo/my-asset/file.txt'
        generated_url = h.url_for_static('/my-asset/file.txt',
                                         qualified=True)
        eq_(generated_url, url)

    @helpers.set_extra_environ('SCRIPT_NAME', '/my/custom/path')
    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_static_with_root_path_and_script_name_env(self):
        url = 'http://example.com/my/custom/path/foo/my-asset/file.txt'
        generated_url = h.url_for_static('/my-asset/file.txt',
                                         qualified=True)
        eq_(generated_url, url)


class TestHelpersUrlForStaticOrExternal(BaseUrlFor):

    def test_url_for_static_or_external(self):
        url = '/assets/ckan.jpg'
        eq_(h.url_for_static_or_external(url), url)

    def test_url_for_static_or_external_works_with_external_urls(self):
        url = 'http://assets.ckan.org/ckan.jpg'
        eq_(h.url_for_static_or_external(url), url)

    def test_url_for_static_or_external_converts_unicode_to_strings(self):
        url = u'/ckan.jpg'
        assert isinstance(h.url_for_static_or_external(url), str)

    def test_url_for_static_or_external_adds_starting_slash_if_needed(self):
        slashless_url = 'ckan.jpg'
        url = '/' + slashless_url
        eq_(h.url_for_static_or_external(slashless_url), url)

    def test_url_for_static_or_external_works_with_protocol_relative_url(self):
        url = '//assets.ckan.org/ckan.jpg'
        eq_(h.url_for_static_or_external(url), url)


class TestHelpersUrlFor(BaseUrlFor):

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_default(self):
        url = '/dataset/my_dataset'
        generated_url = h.url_for(controller='package', action='read',
                                  id='my_dataset')
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_with_locale(self):
        url = '/de/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  locale='de')
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/foo/{{LANG}}')
    def test_url_for_with_locale_object(self):
        url = '/foo/de/dataset/my_dataset'
        generated_url = h.url_for('/dataset/my_dataset',
                                  locale=Locale('de'))
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_not_qualified(self):
        url = '/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=False)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_qualified(self):
        url = 'http://example.com/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=True)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/prefix')
    def test_url_for_qualified_with_root_path(self):
        url = 'http://example.com/my/prefix/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=True)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_qualified_with_locale(self):
        url = 'http://example.com/de/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=True,
                                  locale='de')
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_qualified_with_root_path_and_locale(self):
        url = 'http://example.com/my/custom/path/de/foo/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=True,
                                  locale='de')
        eq_(generated_url, url)

    @helpers.set_extra_environ('SCRIPT_NAME', '/my/custom/path')
    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_qualified_with_root_path_locale_and_script_name_env(self):
        url = 'http://example.com/my/custom/path/de/foo/dataset/my_dataset'
        generated_url = h.url_for(controller='package',
                                  action='read',
                                  id='my_dataset',
                                  qualified=True,
                                  locale='de')
        eq_(generated_url, url)


class TestHelpersUrlForFlaskandPylons2(BaseUrlFor):

    def test_url_for_flask_route_new_syntax(self):
        url = '/api/3'
        generated_url = h.url_for('api.get_api', ver=3)
        eq_(generated_url, url)


class TestHelpersUrlForFlaskandPylons(BaseUrlFor):

    def test_url_for_flask_route_new_syntax(self):
        url = '/api/3'
        generated_url = h.url_for('api.get_api', ver=3)
        eq_(generated_url, url)

    def test_url_for_flask_route_old_syntax(self):
        url = '/api/3'
        generated_url = h.url_for(controller='api', action='get_api', ver=3)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_flask_route_new_syntax_external(self):
        url = 'http://example.com/api/3'
        generated_url = h.url_for('api.get_api', ver=3, _external=True)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_flask_route_old_syntax_external(self):
        url = 'http://example.com/api/3'
        generated_url = h.url_for(controller='api', action='get_api', ver=3, _external=True)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_flask_route_old_syntax_qualified(self):
        url = 'http://example.com/api/3'
        generated_url = h.url_for(controller='api', action='get_api', ver=3, qualified=True)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_flask_route_new_syntax_site_url(self):
        url = '/api/3'
        generated_url = h.url_for('api.get_api', ver=3)
        eq_(generated_url, url)

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_flask_route_old_syntax_site_url(self):
        url = '/api/3'
        generated_url = h.url_for(controller='api', action='get_api', ver=3)
        eq_(generated_url, url)

    def test_url_for_flask_route_new_syntax_request_context(self):
        with self.app.flask_app.test_request_context():
            url = '/api/3'
            generated_url = h.url_for('api.get_api', ver=3)
            eq_(generated_url, url)

    def test_url_for_flask_request_using_pylons_url_for(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')
            plugin = p.get_plugin('test_routing_plugin')
            self.app.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

        res = self.app.get('/flask_route_pylons_url_for')

        assert u'This URL was generated by Pylons' in res.ubody
        assert u'/from_pylons_extension_before_map' in res.ubody

        p.unload('test_routing_plugin')

    def test_url_for_pylons_request_using_flask_url_for(self):

        if not p.plugin_loaded('test_routing_plugin'):
            p.load('test_routing_plugin')

        res = self.app.get('/pylons_route_flask_url_for')

        assert u'This URL was generated by Flask' in res.ubody
        assert u'/api/3' in res.ubody

        p.unload('test_routing_plugin')


class TestHelpersRenderMarkdown(object):

    def test_render_markdown_allow_html(self):
        data = '<h1>moo</h1>'
        eq_(h.render_markdown(data, allow_html=True), data)

    def test_render_markdown_not_allow_html(self):
        data = '<h1>moo</h1>'
        output = '<p>moo</p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link_without_path(self):
        data = 'http://example.com'
        output = '<p><a href="http://example.com" target="_blank" rel="nofollow">http://example.com</a></p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link(self):
        data = 'https://example.com/page.html'
        output = '<p><a href="https://example.com/page.html" target="_blank" rel="nofollow">https://example.com/page.html</a></p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link_ignoring_trailing_punctuation(self):
        data = 'My link: http://example.com/page.html.'
        output = '<p>My link: <a href="http://example.com/page.html" target="_blank" rel="nofollow">http://example.com/page.html</a>.</p>'
        eq_(h.render_markdown(data), output)

    def test_render_naughty_markdown(self):
        data = u'* [Foo (http://foo.bar) * Bar] (http://foo.bar)'
        output = u'<ul>\n<li>[Foo (<a href="http://foo.bar" target="_blank" rel="nofollow">http://foo.bar</a>) * Bar] (<a href="http://foo.bar" target="_blank" rel="nofollow">http://foo.bar</a>)</li>\n</ul>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_with_js(self):
        data = u'[text](javascript: alert(1))'
        output = u'<p><a>text</a></p>'
        eq_(h.render_markdown(data), output)

    def test_event_attributes(self):
        data = u'<p onclick="some.script"><img onmouseover="some.script" src="image.png" /> and text</p>'
        output = u'<p>and text</p>'
        eq_(h.render_markdown(data), output)

    def test_ampersand_in_links(self):
        data = u'[link](/url?a=1&b=2)'
        output = u'<p><a href="/url?a=1&amp;b=2">link</a></p>'
        eq_(h.render_markdown(data), output)

        data = u'http://example.com/page?a=1&b=2'
        output = u'<p><a href="http://example.com/page?a=1&amp;b=2" target="_blank" rel="nofollow">http://example.com/page?a=1&amp;b=2</a></p>'
        eq_(h.render_markdown(data), output)

    def test_tags_h1(self):
        data = u'#heading'
        output = u'<h1>heading</h1>'
        eq_(h.render_markdown(data), output)

    def test_tags_h2(self):
        data = u'##heading'
        output = u'<h2>heading</h2>'
        eq_(h.render_markdown(data), output)

    def test_tags_h3(self):
        data = u'###heading'
        output = u'<h3>heading</h3>'
        eq_(h.render_markdown(data), output)

    def test_tags_img(self):
        data = u'![image](/image.png)'
        output = u'<p><img alt="image" src="/image.png"></p>'
        eq_(h.render_markdown(data), output)

    def test_bold(self):
        data = u'Something **important**'
        output = u'<p>Something <strong>important</strong></p>'
        eq_(h.render_markdown(data), output)

    def test_italics(self):
        data = u'Something *important*'
        output = u'<p>Something <em>important</em></p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_link(self):
        """Asserts links like 'tag:test-tag' work"""
        data = 'tag:test-tag foobar'
        output = '<p><a href="/tag/test-tag">tag:test-tag</a> foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_linked_with_quotes(self):
        """Asserts links like 'tag:"test-tag"' work"""
        data = 'tag:"test-tag" foobar'
        output = '<p><a href="/tag/test-tag">tag:&#34;test-tag&#34;</a> foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_linked_with_quotes_and_space(self):
        """Asserts links like 'tag:"test tag"' work"""
        data = 'tag:"test tag" foobar'
        output = '<p><a href="/tag/test%20tag">tag:&#34;test tag&#34;</a> foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_with_no_opening_quote_only_matches_single_word(self):
        """Asserts that without an opening quote only one word is matched"""
        data = 'tag:test tag" foobar'  # should match 'tag:test'
        output = '<p><a href="/tag/test">tag:test</a> tag" foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_with_no_opening_quote_wont_match_the_closing_quote(self):
        """Asserts that 'tag:test" tag' is matched, but to 'tag:test'"""
        data = 'tag:test" foobar'  # should match 'tag:test'
        output = '<p><a href="/tag/test">tag:test</a>" foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_internal_tag_with_no_closing_quote_does_not_match(self):
        """Asserts that without an opening quote only one word is matched"""
        data = 'tag:"test tag foobar'
        out = h.render_markdown(data)
        assert "<a href" not in out

    def test_tag_names_match_simple_punctuation(self):
        """Asserts punctuation and capital letters are matched in the tag name"""
        data = 'tag:"Test- _." foobar'
        output = '<p><a href="/tag/Test-%20_.">tag:&#34;Test- _.&#34;</a> foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_tag_names_do_not_match_commas(self):
        """Asserts commas don't get matched as part of a tag name"""
        data = 'tag:Test,tag foobar'
        output = '<p><a href="/tag/Test">tag:Test</a>,tag foobar</p>'
        eq_(h.render_markdown(data), output)

    def test_tag_names_dont_match_non_space_whitespace(self):
        """Asserts that the only piece of whitespace matched in a tagname is a space"""
        whitespace_characters = '\t\n\r\f\v'
        for ch in whitespace_characters:
            data = 'tag:Bad' + ch + 'space'
            output = '<p><a href="/tag/Bad">tag:Bad</a>'
            result = h.render_markdown(data)
            assert output in result, '\nGot: %s\nWanted: %s' % (result, output)

    def test_tag_names_with_unicode_alphanumeric(self):
        """Asserts that unicode alphanumeric characters are captured"""
        data = u'tag:"Japanese katakana \u30a1" blah'
        output = u'<p><a href="/tag/Japanese%20katakana%20%E3%82%A1">tag:&#34;Japanese katakana \u30a1&#34;</a> blah</p>'
        eq_(h.render_markdown(data), output)

    def test_normal_link(self):
        data = 'http://somelink/'
        output = '<p><a href="http://somelink/" target="_blank" rel="nofollow">http://somelink/</a></p>'
        eq_(h.render_markdown(data), output)

    def test_normal_link_with_anchor(self):
        data = 'http://somelink.com/#anchor'
        output = '<p><a href="http://somelink.com/#anchor" target="_blank" rel="nofollow">http://somelink.com/#anchor</a></p>'
        eq_(h.render_markdown(data), output)

    def test_auto_link(self):
        data = 'http://somelink.com'
        output = '<p><a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a></p>'
        eq_(h.render_markdown(data), output)

    def test_auto_link_after_whitespace(self):
        data = 'go to http://somelink.com'
        output = '<p>go to <a href="http://somelink.com" target="_blank" rel="nofollow">http://somelink.com</a></p>'
        eq_(h.render_markdown(data), output)

    def test_malformed_link_1(self):
        data = u'<a href=\u201dsomelink\u201d>somelink</a>'
        output = '<p>somelink</p>'
        eq_(h.render_markdown(data), output)


class TestHelpersRemoveLineBreaks(object):

    def test_remove_linebreaks_removes_linebreaks(self):
        test_string = 'foo\nbar\nbaz'
        result = h.remove_linebreaks(test_string)

        assert result.find('\n') == -1,\
            '"remove_linebreaks" should remove line breaks'

    def test_remove_linebreaks_casts_into_unicode(self):
        class UnicodeLike(text_type):
            pass

        test_string = UnicodeLike('foo')
        result = h.remove_linebreaks(test_string)

        strType = u''.__class__
        assert result.__class__ == strType,\
            '"remove_linebreaks" casts into unicode()'


class TestLicenseOptions(object):
    def test_includes_existing_license(self):
        licenses = h.license_options('some-old-license')
        eq_(dict(licenses)['some-old-license'], 'some-old-license')
        # and it is first on the list
        eq_(licenses[0][0], 'some-old-license')


class TestUnifiedResourceFormat(object):
    def test_unified_resource_format_by_extension(self):
        eq_(h.unified_resource_format('xls'), 'XLS')

    def test_unified_resource_format_by_description(self):
        eq_(h.unified_resource_format('Excel document'), 'XLS')

    def test_unified_resource_format_by_primary_mimetype(self):
        eq_(h.unified_resource_format('application/vnd.ms-excel'), 'XLS')

    def test_unified_resource_format_by_alternative_description(self):
        eq_(h.unified_resource_format('application/msexcel'), 'XLS')

    def test_unified_resource_format_by_alternative_description2(self):
        eq_(h.unified_resource_format('Excel'), 'XLS')

    def test_autodetect_tsv(self):

        eq_(h.unified_resource_format('tsv'), 'TSV')

        eq_(h.unified_resource_format('text/tab-separated-values'), 'TSV')

        eq_(h.unified_resource_format('text/tsv'), 'TSV')


class TestGetDisplayTimezone(object):
    @helpers.change_config('ckan.display_timezone', '')
    def test_missing_config(self):
        eq_(h.get_display_timezone(), pytz.timezone('utc'))

    @helpers.change_config('ckan.display_timezone', 'server')
    def test_server_timezone(self):
        eq_(h.get_display_timezone(), tzlocal.get_localzone())

    @helpers.change_config('ckan.display_timezone', 'America/New_York')
    def test_named_timezone(self):
        eq_(h.get_display_timezone(), pytz.timezone('America/New_York'))


class TestCleanHtml(object):
    def test_disallowed_tag(self):
        eq_(h.clean_html('<b><bad-tag>Hello'),
            u'<b>&lt;bad-tag&gt;Hello&lt;/bad-tag&gt;</b>')

    def test_non_string(self):
        # allow a datetime for compatibility with older ckanext-datapusher
        eq_(h.clean_html(datetime.datetime(2018, 1, 5, 10, 48, 23, 463511)),
            u'2018-01-05 10:48:23.463511')


class TestHelperException(helpers.FunctionalTestBase):

    @raises(ckan.exceptions.HelperError)
    def test_helper_exception_non_existing_helper_as_attribute(self):
        '''Calling a non-existing helper on `h` raises a HelperException.'''
        if not p.plugin_loaded('test_helpers_plugin'):
            p.load('test_helpers_plugin')

        app = self._get_test_app()

        app.get('/broken_helper_as_attribute')

        p.unload('test_helpers_plugin')

    @raises(ckan.exceptions.HelperError)
    def test_helper_exception_non_existing_helper_as_item(self):
        '''Calling a non-existing helper on `h` raises a HelperException.'''
        if not p.plugin_loaded('test_helpers_plugin'):
            p.load('test_helpers_plugin')

        app = self._get_test_app()

        app.get('/broken_helper_as_item')

        p.unload('test_helpers_plugin')

    def test_helper_existing_helper_as_attribute(self):
        '''Calling an existing helper on `h` doesn't raises a
        HelperException.'''

        if not p.plugin_loaded('test_helpers_plugin'):
            p.load('test_helpers_plugin')

        app = self._get_test_app()

        res = app.get('/helper_as_attribute')

        ok_('My lang is: en' in res.body)

        p.unload('test_helpers_plugin')

    def test_helper_existing_helper_as_item(self):
        '''Calling an existing helper on `h` doesn't raises a
        HelperException.'''

        if not p.plugin_loaded('test_helpers_plugin'):
            p.load('test_helpers_plugin')

        app = self._get_test_app()

        res = app.get('/helper_as_item')

        ok_('My lang is: en' in res.body)

        p.unload('test_helpers_plugin')


class TestHelpersPlugin(p.SingletonPlugin):

    p.implements(p.IRoutes, inherit=True)

    controller = 'ckan.tests.lib.test_helpers:TestHelperController'

    def after_map(self, _map):

        _map.connect('/broken_helper_as_attribute',
                     controller=self.controller,
                     action='broken_helper_as_attribute')

        _map.connect('/broken_helper_as_item',
                     controller=self.controller,
                     action='broken_helper_as_item')

        _map.connect('/helper_as_attribute',
                     controller=self.controller,
                     action='helper_as_attribute')

        _map.connect('/helper_as_item',
                     controller=self.controller,
                     action='helper_as_item')

        return _map


class TestHelperController(p.toolkit.BaseController):

    def broken_helper_as_attribute(self):
        return base.render('tests/broken_helper_as_attribute.html')

    def broken_helper_as_item(self):
        return base.render('tests/broken_helper_as_item.html')

    def helper_as_attribute(self):
        return base.render('tests/helper_as_attribute.html')

    def helper_as_item(self):
        return base.render('tests/helper_as_item.html')
