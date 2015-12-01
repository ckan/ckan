import nose
import i18n

import ckan.lib.helpers as h
import ckan.exceptions
from ckan.tests import helpers

eq_ = nose.tools.eq_
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
