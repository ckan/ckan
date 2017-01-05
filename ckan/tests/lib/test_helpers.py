# encoding: utf-8

import nose
import pytz
import tzlocal
from babel import Locale

import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.exceptions
from ckan.tests import helpers
import ckan.lib.base as base

ok_ = nose.tools.ok_
eq_ = nose.tools.eq_
raises = nose.tools.raises
CkanUrlException = ckan.exceptions.CkanUrlException


class TestHelpersUrlForStatic(object):

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
        generated_url = h.url_for_static('/my-asset/file.txt', qualified=True)
        eq_(generated_url, url)

    @helpers.set_extra_environ('SCRIPT_NAME', '/my/custom/path')
    @helpers.change_config('ckan.site_url', 'http://example.com')
    @helpers.change_config('ckan.root_path', '/my/custom/path/{{LANG}}/foo')
    def test_url_for_static_with_root_path_and_script_name_env(self):
        url = 'http://example.com/my/custom/path/foo/my-asset/file.txt'
        generated_url = h.url_for_static('/my-asset/file.txt', qualified=True)
        eq_(generated_url, url)


class TestHelpersUrlForStaticOrExternal(object):

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


class TestHelpersUrlFor(object):

    @helpers.change_config('ckan.site_url', 'http://example.com')
    def test_url_for_default(self):
        url = '/dataset/my_dataset'
        generated_url = h.url_for(controller='package', action='read', id='my_dataset')
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


class TestHelpersRemoveLineBreaks(object):

    def test_remove_linebreaks_removes_linebreaks(self):
        test_string = 'foo\nbar\nbaz'
        result = h.remove_linebreaks(test_string)

        assert result.find('\n') == -1,\
            '"remove_linebreaks" should remove line breaks'

    def test_remove_linebreaks_casts_into_unicode(self):
        class UnicodeLike(unicode):
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
