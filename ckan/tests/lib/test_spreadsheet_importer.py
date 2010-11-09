import os

from pylons import config

import ckan.lib.importer as importer
import ckan.lib.spreadsheet_importer as spreadsheet_importer

EXAMPLES_DIR = 'ckan/tests/misc/'
EXAMPLE_TESTFILE_FILEPATH = os.path.join(config['here'], EXAMPLES_DIR, 'test_importer_example')
FULL_TESTFILE_FILEPATH = os.path.join(config['here'], EXAMPLES_DIR, 'test_importer_full')
XL_EXTENSION = '.xls'
CSV_EXTENSION = '.csv'
EXTENSIONS = [CSV_EXTENSION, XL_EXTENSION]
SPREADSHEET_CLASS_MAP = {XL_EXTENSION:spreadsheet_importer.XlData,
                         CSV_EXTENSION:spreadsheet_importer.CsvData}

class BasicLogger:
    def __init__(self):
        self.log = []
        
    def log(self, msg):
        self.log.append(msg)
    

class TestSpreadsheetData:
    def test_0_example_file_by_filepath(self):
        for extension in EXTENSIONS:
            logger = BasicLogger()
            filepath = EXAMPLE_TESTFILE_FILEPATH + extension
            data = SPREADSHEET_CLASS_MAP[extension](logger, filepath=filepath)
            self.assert_example_data(data)
            assert logger.log == [], logger.log
        
    def test_1_example_file_by_buf(self):
        for extension in EXTENSIONS:
            logger = BasicLogger()
            filepath = EXAMPLE_TESTFILE_FILEPATH + extension
            f = open(filepath, 'rb')
            buf = f.read()
            f.close()
            data = SPREADSHEET_CLASS_MAP[extension](logger, buf=buf)
            self.assert_example_data(data)
            assert logger.log == [], logger.log

    def assert_example_data(self, data):
        num_rows = data.get_num_rows()
        assert 3 <= num_rows <= 4, num_rows
        rows = data.get_all_rows()
        assert len(rows) == num_rows
        first_row = data.get_row(0)
        assert first_row == rows[0]
        assert rows[0] == [u'name', u'title', u'resource-0-url', u'resource-0-format', u'resource-0-description', u'tags'], rows[0]
        assert rows[1] == [u'wikipedia', u'Wikipedia', u'http://static.wikipedia.org/downloads/2008-06/en/wikipedia-en-html.tar.7z', u'html', u'In English', u'encyclopedia reference'], rows[1]
        # xl gives None and csv gives u'' for blank cells
        assert rows[2] == [u'tviv', u'TV IV', u'http://tviv.org/Category:Grids', u'', u'', u'tv encyclopedia'] or \
               rows[2] == [u'tviv', u'TV IV', u'http://tviv.org/Category:Grids', None, None, u'tv encyclopedia'], rows[2]
        if num_rows == 4:
            assert rows[3] == [], rows[3]

def get_example_data():
    logger = BasicLogger()
    extension = XL_EXTENSION
    filepath = EXAMPLE_TESTFILE_FILEPATH + extension
    return SPREADSHEET_CLASS_MAP[extension](logger, filepath=filepath)

class TestDataRecords:
    def test_0_example(self):
        data = get_example_data()
        data_records = spreadsheet_importer.SpreadsheetDataRecords(data, 'title')
        assert data_records.titles == data.get_row(0), data_records.titles
        records = [record for record in data_records.records]
        assert len(records) == 2, records
        assert records[0].items() == [
            (u'name', u'wikipedia'),
            (u'title', u'Wikipedia'),
            (u'resource-0-url', u'http://static.wikipedia.org/downloads/2008-06/en/wikipedia-en-html.tar.7z'),
            (u'resource-0-format', u'html'),
            (u'resource-0-description', u'In English'),
            (u'tags', u'encyclopedia reference'),
            ], records[0].items()
        assert records[1].items() == [
            (u'name', u'tviv'),
            (u'title', u'TV IV'),
            (u'resource-0-url', u'http://tviv.org/Category:Grids'),
            (u'resource-0-format', None),
            (u'resource-0-description', None),
            (u'tags', u'tv encyclopedia'),
            ], records[1].items()

class TestPackageImporter:
    def test_munge(self):
        def test_munge(title, expected_munge):
            munge = spreadsheet_importer.SpreadsheetPackageImporter.munge(title)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_munge('Adult participation in learning', 'adult_participation_in_learning')
        test_munge('Alcohol Profile: Alcohol-specific hospital admission, males', 'alcohol_profile_-_alcohol-specific_hospital_admission_males')
        test_munge('Age and limiting long-term illness by NS-SeC', 'age_and_limiting_long-term_illness_by_ns-sec')
        test_munge('Higher Education Statistics: HE qualifications obtained in the UK by level, mode of study, domicile, gender, class of first degree and subject area 2001/02', 'higher_education_statistics_-_he_qualifications_obtained_in_the_uk_by_level_mode_of_stu-2001-02')        
        
    def test_0_example_by_filepath(self):
        for extension in EXTENSIONS:
            filepath = EXAMPLE_TESTFILE_FILEPATH + extension
            package_import = spreadsheet_importer.SpreadsheetPackageImporter(filepath=filepath)
            self.assert_example_package_import(package_import)

    def assert_example_package_import(self, package_import):
        pkg_dicts = [pkg_dict for pkg_dict in package_import.pkg_dict()]
        assert len(pkg_dicts) == 2, pkg_dicts
        assert pkg_dicts[0].items() == [(u'name', u'wikipedia'), (u'title', u'Wikipedia'), ('resources', [{'url': u'http://static.wikipedia.org/downloads/2008-06/en/wikipedia-en-html.tar.7z', 'hash': u'', 'description': u'In English', 'format': u'html'}]), (u'tags', u'encyclopedia reference')], pkg_dicts[0].items()
        assert pkg_dicts[1].items() == [(u'name', u'tviv'), (u'title', u'TV IV'), ('resources', [{'url': u'http://tviv.org/Category:Grids', 'hash': u'', 'description': u'', 'format': u''}]), (u'tags', u'tv encyclopedia')], pkg_dicts[1].items()        
