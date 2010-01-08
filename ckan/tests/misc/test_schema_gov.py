import ckan.lib.schema_gov
from ckan.tests import *

class TestDate:
    def test_0_form_to_db(self):
        out = ckan.lib.schema_gov.DateType.form_to_db('27/2/2008')
        assert out == '2008-02-27', out
        out = ckan.lib.schema_gov.DateType.form_to_db('27/2/08')
        assert out == '2008-02-27', out
        out = ckan.lib.schema_gov.DateType.form_to_db('27/2/98')
        assert out == '1998-02-27', out
        out = ckan.lib.schema_gov.DateType.form_to_db('2/2008')
        assert out == '2008-02', out
        out = ckan.lib.schema_gov.DateType.form_to_db('2008')
        assert out == '2008', out

    def test_1_form_validator(self):
        assert ckan.lib.schema_gov.DateType.form_validator('25/2/2009') is None
        assert ckan.lib.schema_gov.DateType.form_validator('humpty')
        assert ckan.lib.schema_gov.DateType.form_validator('2135')
        assert ckan.lib.schema_gov.DateType.form_validator('345')
        assert ckan.lib.schema_gov.DateType.form_validator('2000BC')
        assert ckan.lib.schema_gov.DateType.form_validator('45/2009')
        assert ckan.lib.schema_gov.DateType.form_validator('-2/2009')
        assert ckan.lib.schema_gov.DateType.form_validator('35/3/2009')
        assert ckan.lib.schema_gov.DateType.form_validator('') is None
        
    def test_2_db_to_form(self):
        out = ckan.lib.schema_gov.DateType.db_to_form('2008-02-27')
        assert out == '27/2/2008', out
        out = ckan.lib.schema_gov.DateType.db_to_form('2008-02')
        assert out == '2/2008', out
        out = ckan.lib.schema_gov.DateType.db_to_form('2008')
        assert out == '2008', out
        out = ckan.lib.schema_gov.DateType.db_to_form('humpty')
        assert out == 'humpty', out
        out = ckan.lib.schema_gov.DateType.db_to_form('27/2/2008')
        assert out == '27/2/2008', out
        
