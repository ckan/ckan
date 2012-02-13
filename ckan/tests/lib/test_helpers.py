# -*- coding: utf-8 -*-
import time
import datetime
from nose.tools import assert_equal

from ckan.tests import *
from ckan.lib import helpers as h


WITH_HTML = u'''Data exposed: &mdash;
Size of dump and data set: size?
Notes: this is the classic RDF source but historically has had some problems with RDF correctness.
'''

WITH_UNICODE = u'''[From the project website] This project collects information on China’s foreign aid from the China Commerce Yearbook (中国商务年鉴) and the Almanac of China’s Foreign Economic Relations & Trade (中国对外经济贸易年间), published annually by China’s Ministry of Commerce (MOFCOM). Data is reported for each year between 1990 and 2005, with the exception of 2002, in which year China’s Ministry of Commerce published no project-level data on its foreign aid giving.'''

class TestHelpers(TestController):
        
    def test_extract_markdown(self):
        assert "Data exposed" in h.markdown_extract(WITH_HTML)
        assert "collects information" in h.markdown_extract(WITH_UNICODE)

    def test_render_datetime(self):
        res = h.render_datetime(datetime.datetime(2008, 4, 13, 20, 40, 20, 123456))
        assert_equal(res, 'Apr 13, 2008')

    def test_render_datetime_but_from_string(self):
        res = h.render_datetime('2008-04-13T20:40:20.123456')
        assert_equal(res, 'Apr 13, 2008')

    def test_render_datetime_blank(self):
        res = h.render_datetime(None)
        assert_equal(res, '')

    def test_datetime_to_date_str(self):
        res = h.datetime_to_date_str(datetime.datetime(2008, 4, 13, 20, 40, 20, 123456))
        assert_equal(res, '2008-04-13T20:40:20.123456')

    def test_date_str_to_datetime(self):
        res = h.date_str_to_datetime('2008-04-13T20:40:20.123456')
        assert_equal(res, datetime.datetime(2008, 4, 13, 20, 40, 20, 123456))

    def test_date_str_to_datetime_without_microseconds(self):
        # This occurs in ckan.net timestamps - not sure how they appeared
        res = h.date_str_to_datetime('2008-04-13T20:40:20')
        assert_equal(res, datetime.datetime(2008, 4, 13, 20, 40, 20))

    def test_time_ago_in_words_from_str(self):
        two_months_ago = datetime.datetime.now() - datetime.timedelta(days=65)
        two_months_ago_str = h.datetime_to_date_str(two_months_ago)
        res = h.time_ago_in_words_from_str(two_months_ago_str)
        assert_equal(res, '2 months')

    def test_gravatar(self):
        email = 'zephod@gmail.com'
        expected =['<a href="https://gravatar.com/"',
                '<img src="http://gravatar.com/avatar/7856421db6a63efa5b248909c472fbd2?s=200&amp;d=identicon"', '</a>']
        # Hash the email address
        import hashlib
        email_hash = hashlib.md5(email).hexdigest()
        res = h.linked_gravatar(email_hash, 200)
        for e in expected:
            assert e in res, (e,res)
