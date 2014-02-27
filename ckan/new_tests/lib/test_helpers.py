import nose

import ckan.lib.helpers as h

eq_ = nose.tools.eq_


class TestHelpers(object):
    def test_url_for_static(self):
        url = '/assets/ckan.jpg'
        eq_(h.url_for_static(url), url)

    def test_url_for_static_adds_starting_slash_if_url_doesnt_have_it(self):
        slashless_url = 'ckan.jpg'
        url = '/' + slashless_url
        eq_(h.url_for_static(slashless_url), url)

    def test_url_for_static_works_with_absolute_urls(self):
        url = 'http://assets.ckan.org/ckan.jpg'
        eq_(h.url_for_static(url), url)

    def test_url_for_static_works_with_protocol_relative_urls(self):
        url = '//assets.ckan.org/ckan.jpg'
        eq_(h.url_for_static(url), url)

    def test_url_for_static_converts_unicode_strings_to_regular_strings(self):
        url = u'/ckan.jpg'
        assert isinstance(h.url_for_static(url), str)
