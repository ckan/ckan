# encoding: utf-8

import math
import string

from nose.tools import assert_equal, assert_true, assert_false, assert_in
from bs4 import BeautifulSoup

from routes import url_for

import ckan.tests.helpers as helpers
from ckan.tests import factories

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


def _make_tag_list(n=26):
    '''Returns a list of tag dicts, starting with 'aa, bb, ..., zz', then
    'aaa, bbb, ..., zzz', etc. Tags must be at least 2 characters.'''
    lc = string.lowercase
    lc_len = len(lc)
    return [{'name': lc[i % lc_len] * int(math.ceil(i / lc_len) + 2)}
            for i in range(0, n)]


class TestTagIndex(helpers.FunctionalTestBase):

    def test_tags_listed_under_50(self):
        '''Tag index lists tags under 50 tags.'''
        app = self._get_test_app()
        expected_tags = _make_tag_list(49)
        factories.Dataset(tags=expected_tags)

        tag_index_url = url_for(controller='tag', action='index')
        tag_response = app.get(tag_index_url)

        tag_response_html = BeautifulSoup(tag_response.body)
        tags = [t.string for t in tag_response_html.select('.tag')]

        expected_tag_values = [t['name'] for t in expected_tags]

        assert_equal(len(tags), 49)
        for t in expected_tag_values:
            assert_true(t in tags)

        # no pagination
        assert_false(tag_response_html.select('.pagination'))

    def test_tags_listed_over_50(self):
        '''Tag index lists tags over 50 tags.'''
        app = self._get_test_app()
        expected_tags = _make_tag_list(51)
        factories.Dataset(tags=expected_tags)

        tag_index_url = url_for(controller='tag', action='index')
        tag_response = app.get(tag_index_url)

        tag_response_html = BeautifulSoup(tag_response.body)
        tags = [t.string for t in tag_response_html.select('.tag')]

        expected_tag_values = [t['name'] for t in expected_tags]

        assert_equal(len(tags), 2)
        assert_true(expected_tag_values)
        for t in [u'aa', u'aaa']:
            assert_true(t in tags)

        # has pagination
        assert_true(tag_response_html.select('.pagination'))

    def test_tag_search(self):
        '''Tag search returns expected results'''
        app = self._get_test_app()
        expected_tags = _make_tag_list(50)
        expected_tags.append({'name': 'find-me'})
        factories.Dataset(tags=expected_tags)

        tag_index_url = url_for(controller='tag', action='index')
        tag_response = app.get(tag_index_url)

        search_form = tag_response.forms[1]
        search_form['q'] = 'find-me'
        search_response = webtest_submit(search_form, status=200)

        search_response_html = BeautifulSoup(search_response.body)
        tags = [t.string for t in search_response_html.select('.tag')]

        assert_equal(len(tags), 1)
        assert_true('find-me' in tags)

        # no pagination
        assert_false(search_response_html.select('.pagination'))

    def test_tag_search_no_results(self):
        '''Searching for tags yielding no results'''
        app = self._get_test_app()
        expected_tags = _make_tag_list(50)
        factories.Dataset(tags=expected_tags)

        tag_index_url = url_for(controller='tag', action='index')
        tag_response = app.get(tag_index_url)

        search_form = tag_response.forms[1]
        search_form['q'] = 'find-me'
        search_response = webtest_submit(search_form, status=200)

        search_response_html = BeautifulSoup(search_response.body)
        tags = [t.string for t in search_response_html.select('.tag')]

        assert_equal(len(tags), 0)
        assert_true('find-me' not in tags)

        # no pagination
        assert_false(search_response_html.select('.pagination'))


class TestTagRead(helpers.FunctionalTestBase):

    def test_tag_read_redirects_to_dataset_search(self):
        app = self._get_test_app()
        factories.Dataset(title='My Other Dataset', tags=[{'name': 'find-me'}])

        tag_url = url_for(controller='tag', action='read', id='find-me')
        tag_response = app.get(tag_url, status=302)
        assert_equal(tag_response.headers['Location'],
                     'http://test.ckan.net/dataset?tags=find-me')

    def test_tag_read_not_found(self):
        '''Attempting access to non-existing tag returns a 404'''
        app = self._get_test_app()
        factories.Dataset(title='My Other Dataset', tags=[{'name': 'find-me'}])

        tag_url = url_for(controller='tag', action='read', id='not-here')
        app.get(tag_url, status=404)
