import formalchemy

from ckan.lib.field_types import *
from ckan.tests import *
from unittest import TestCase

class TestDate(TestCase):
    def test_0_parse_timedate(self):
        expected_parse = {
            'form':[
                ('27/2/2008', 'DD/MM/YYYY', [2008, 2, 27]),
                ('27/2/08', 'DD/MM/YYYY', [2008, 2, 27]),
                ('27/2/98', 'DD/MM/YYYY', [1998, 2, 27]),
                ('27-Feb-2008', 'DD/MM/YYYY', [2008, 2, 27]),
                ('2/2008', 'MM/YYYY', [2008, 2]),
                ('Jun-2008', 'MM/YYYY', [2008, 6]),
                ('2008', 'YYYY', [2008]),
                ('13:16 27/2/2008', 'HH:MM DD/MM/YYYY', [2008, 2, 27, 13, 16]),
                ('2/11/67 9:04', 'DD/MM/YYYY HH:MM', [1967, 11, 2, 9, 04]),
                ],
            'db':[
                ('2008', 'YYYY', [2008]),
                ('2008-02-27', 'YYYY-MM-DD', [2008, 2, 27]),
                ],
            }
        expected_fields = ('year', 'month', 'day', 'hour', 'minute')
        for format_type in ('form', 'db'):
            for timedate_str, expected_format, expected_list in expected_parse[format_type]:
                expected_dict = {}
                for index, expected_val in enumerate(expected_list):
                    expected_dict[expected_fields[index]] = expected_val
                expected_dict['readable_format'] = expected_format
                out = DateType.parse_timedate(timedate_str, format_type)
                assert out == expected_dict, '%s value %r gives %r, not %r' % (format_type, timedate_str, out, expected_dict)
        
    def test_1_form_to_db(self):
        expected_form_to_db = [
            ('27/2/2008', '2008-02-27'),
            ('27/2/08', '2008-02-27'),
            ('27/2/98', '1998-02-27'),
            ('27-Feb-2008', '2008-02-27'),
            ('2/2008', '2008-02'),
            ('Jun-2008', '2008-06'),
            ('2008', '2008'),
            ('13:16 27/2/2008', '2008-02-27 13:16'),
            ('9:04 2/11/67', '1967-11-02 09:04'),
            ]
        for form_date, expected_db_date in expected_form_to_db:
            out = DateType.form_to_db(form_date)
            assert out == expected_db_date, 'From %r matched %r, not %r' % (form_date, out, expected_db_date)

    def test_2_form_validator(self):
        valid_dates = ['25/2/2009', '25/Feb/2009', '', ' ', None]
        invalid_dates = ['humpty', '2135', '345', '2000BC', '45/2009',
                         '-2/2009', '35/3/2009', '35/Feb/2009', '25/ABC/2009',
                         '24:03 2/11/67']
        for date_str in valid_dates:
            assert DateType.form_validator(date_str) is None, date_str
        for date_str in invalid_dates:
            self.assertRaises(formalchemy.ValidationError, DateType.form_validator, date_str)
        
    def test_3_db_to_form(self):
        expected_db_to_form = [
            ('2008-02-27 12:20', '12:20 27/2/2008'),
            ('2008-02-27', '27/2/2008'),
            ('2008-02', '2/2008'),
            ('2008', '2008'),
            ('10/2/03', '3/2/2010'),
            ('humpty', 'humpty'), #invalid
            ('27/2/2008', '27/2/2008'), #invalid
            ]
        for db_date, expected_form_date in expected_db_to_form:
            out = DateType.db_to_form(db_date)
            assert out == expected_form_date, 'From %r gives %r, not %r' % (db_date, out, expected_form_date)

    def test_4_iso_to_db(self):
        out = DateType.iso_to_db('Wed, 06 Jan 2010 09:30:00', '%a, %d %b %Y %H:%M:%S')
        assert out == '2010-01-06', out

    def test_5_strip_iso_timezone(self):
        out = DateType.strip_iso_timezone('Wed, 06 Jan 2010 09:30:00 GMT')
        assert out == 'Wed, 06 Jan 2010 09:30:00', out
        out = DateType.strip_iso_timezone('Wed, 06 Jan 2010 09:30:00 +0100')
        assert out == 'Wed, 06 Jan 2010 09:30:00', out

