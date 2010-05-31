import formalchemy
from unittest import TestCase

from ckan.lib.field_types import *
import ckan.lib.schema_gov as schema_gov
from ckan.tests import *

class TestDate(TestCase):
    def test_0_form_to_db(self):
        out = DateType.form_to_db('27/2/2008')
        assert out == '2008-02-27', out
        out = DateType.form_to_db('27/2/08')
        assert out == '2008-02-27', out
        out = DateType.form_to_db('27/2/98')
        assert out == '1998-02-27', out
        out = DateType.form_to_db('27-Feb-2008')
        assert out == '2008-02-27', out
        out = DateType.form_to_db('2/2008')
        assert out == '2008-02', out
        out = DateType.form_to_db('Jun-2008')
        assert out == '2008-06', out
        out = DateType.form_to_db('2008')
        assert out == '2008', out

    def test_1_form_validator(self):
        valid_dates = ['25/2/2009', '25/Feb/2009', '']
        invalid_dates = ['humpty', '2135', '345', '2000BC', '45/2009',
                         '-2/2009', '35/3/2009', '35/Feb/2009', '25/ABC/2009']
        for date_str in valid_dates:
            print date_str
            assert DateType.form_validator(date_str) is None, date_str
        for date_str in invalid_dates:
            print date_str
            self.assertRaises(formalchemy.ValidationError, DateType.form_validator, date_str)
        
    def test_2_db_to_form(self):
        out = DateType.db_to_form('2008-02-27')
        assert out == '27/2/2008', out
        out = DateType.db_to_form('2008-02')
        assert out == '2/2008', out
        out = DateType.db_to_form('2008')
        assert out == '2008', out
        out = DateType.db_to_form('humpty')
        assert out == 'humpty', out
        out = DateType.db_to_form('27/2/2008')
        assert out == '27/2/2008', out

    def test_3_iso_to_db(self):
        out = DateType.iso_to_db('Wed, 06 Jan 2010 09:30:00', '%a, %d %b %Y %H:%M:%S')
        assert out == '2010-01-06', out

    def test_4_strip_iso_timezone(self):
        out = DateType.strip_iso_timezone('Wed, 06 Jan 2010 09:30:00 GMT')
        assert out == 'Wed, 06 Jan 2010 09:30:00', out
        out = DateType.strip_iso_timezone('Wed, 06 Jan 2010 09:30:00 +0100')
        assert out == 'Wed, 06 Jan 2010 09:30:00', out

class TestGovTags(object):
    def test_tags_parse(self):
        def test_parse(tag_str, expected_tags):
            tags = schema_gov.tags_parse(tag_str)
            assert tags == expected_tags, 'Got %s not %s' % (tags, expected_tags)
        test_parse('one two three', ['one', 'two', 'three'])
        test_parse('one, two, three', ['one', 'two', 'three'])
        test_parse('one,two,three', ['one', 'two', 'three'])
        test_parse('one-two,three', ['one-two', 'three'])
        test_parse('One, two&three', ['one', 'twothree'])
        test_parse('One, two_three', ['one', 'two-three'])
        test_parse('ordnance survey stuff', ['ordnance-survey', 'stuff'])
        test_parse('ordnance stuff survey', ['ordnance', 'stuff', 'survey'])
