import unittest
import ckan.lib.navl.dictization_functions as df
import ckanext.datastore.logic.schema as schema


class TestDateFormatValidator(unittest.TestCase):
    def test_is_valid_date_format(self):
        schema.is_date_format('yyyymmdd', {})
        schema.is_date_format('ddmmYyyy', {})
        schema.is_date_format('Mmddyyyy', {})

    def test_is_invalid_date_format(self):
        self.assertRaises(
            df.Invalid,
            schema.is_date_format,
            'yyyy-mm-dd%%',
            {}
        )
