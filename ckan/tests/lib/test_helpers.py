# -*- coding: utf-8 -*-
import time

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