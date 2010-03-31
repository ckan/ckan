import ckan.lib.schema_gov as schema_gov
from ckan.tests import *

class TestDate:
    def test_0_form_to_db(self):
        out = schema_gov.DateType.form_to_db('27/2/2008')
        assert out == '2008-02-27', out
        out = schema_gov.DateType.form_to_db('27/2/08')
        assert out == '2008-02-27', out
        out = schema_gov.DateType.form_to_db('27/2/98')
        assert out == '1998-02-27', out
        out = schema_gov.DateType.form_to_db('27-Feb-2008')
        assert out == '2008-02-27', out
        out = schema_gov.DateType.form_to_db('2/2008')
        assert out == '2008-02', out
        out = schema_gov.DateType.form_to_db('Jun-2008')
        assert out == '2008-06', out
        out = schema_gov.DateType.form_to_db('2008')
        assert out == '2008', out

    def test_1_form_validator(self):
        assert schema_gov.DateType.form_validator('25/2/2009') is None
        assert schema_gov.DateType.form_validator('humpty')
        assert schema_gov.DateType.form_validator('2135')
        assert schema_gov.DateType.form_validator('345')
        assert schema_gov.DateType.form_validator('2000BC')
        assert schema_gov.DateType.form_validator('45/2009')
        assert schema_gov.DateType.form_validator('-2/2009')
        assert schema_gov.DateType.form_validator('35/3/2009')
        assert schema_gov.DateType.form_validator('25/Feb/2009') is None
        assert schema_gov.DateType.form_validator('35/ABC/2009')
        assert schema_gov.DateType.form_validator('') is None
        
    def test_2_db_to_form(self):
        out = schema_gov.DateType.db_to_form('2008-02-27')
        assert out == '27/2/2008', out
        out = schema_gov.DateType.db_to_form('2008-02')
        assert out == '2/2008', out
        out = schema_gov.DateType.db_to_form('2008')
        assert out == '2008', out
        out = schema_gov.DateType.db_to_form('humpty')
        assert out == 'humpty', out
        out = schema_gov.DateType.db_to_form('27/2/2008')
        assert out == '27/2/2008', out
        
    def test_3_tags_parse(self):
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
