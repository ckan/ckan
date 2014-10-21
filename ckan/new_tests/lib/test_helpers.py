import nose

import ckan.lib.helpers as h
import ckan.exceptions

eq_ = nose.tools.eq_
CkanUrlException = ckan.exceptions.CkanUrlException


class TestHelpers(object):
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

    def test_render_markdown_allow_html(self):
        data = '<h1>moo</h1>'
        eq_(h.render_markdown(data, allow_html=True), data)

    def test_render_markdown_not_allow_html(self):
        data = '<h1>moo</h1>'
        output = '<p>moo\n</p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link_without_path(self):
        data = 'http://example.com'
        output = '<p><a href="http://example.com" target="_blank" rel="nofollow">http://example.com</a>\n</p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link(self):
        data = 'https://example.com/page.html'
        output = '<p><a href="https://example.com/page.html" target="_blank" rel="nofollow">https://example.com/page.html</a>\n</p>'
        eq_(h.render_markdown(data), output)

    def test_render_markdown_auto_link_ignoring_trailing_punctuation(self):
        data = 'My link: http://example.com/page.html.'
        output = '<p>My link: <a href="http://example.com/page.html" target="_blank" rel="nofollow">http://example.com/page.html</a>.\n</p>'
        eq_(h.render_markdown(data), output)
