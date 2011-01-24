import os

from pylons import config

import ckan.lib.importer as importer
import ckan.lib.spreadsheet_importer as spreadsheet_importer

EXAMPLES_DIR = 'ckan/tests/misc/'
EXAMPLE_FILEBASE = 'test_importer'
EXAMPLE_TESTFILE_SUFFIX = '_example'
EXAMPLE_BIS_TESTFILE_SUFFIX = '_bis_example'
CKAN_SRC_DIR = config['here']
XL_EXTENSION = '.xls'
CSV_EXTENSION = '.csv'
EXTENSIONS = [CSV_EXTENSION, XL_EXTENSION]
SPREADSHEET_DATA_MAP = {XL_EXTENSION:spreadsheet_importer.XlData,
                        CSV_EXTENSION:spreadsheet_importer.CsvData}

class ExampleFiles(object):
    def __init__(self, examples_dir, example_filebase):
        '''
        Easy accessor for info about test fixture files. 
        @param examples_dir - relative from pyenv/src/ckan
        '''
        self.examples_dir = examples_dir
        self.example_filebase = example_filebase
        
    def get_spreadsheet_filepath(self, test_file_suffix, extension):
        return os.path.join(CKAN_SRC_DIR, self.examples_dir, self.example_filebase + test_file_suffix + extension)

    def get_data(self, test_file_suffix, extension=XL_EXTENSION):
        logger = BasicLogger()
        filepath = self.get_spreadsheet_filepath(test_file_suffix, extension)
        return SPREADSHEET_DATA_MAP[extension](logger, filepath=filepath)

examples = ExampleFiles(EXAMPLES_DIR, EXAMPLE_FILEBASE)

class BasicLogger:
    def __init__(self):
        self.log = []


class TestSpreadsheetData:
    def test_0_example_file_by_filepath(self):
        for extension in EXTENSIONS:
            logger = BasicLogger()
            filepath = examples.get_spreadsheet_filepath(EXAMPLE_TESTFILE_SUFFIX, extension)
            data = SPREADSHEET_DATA_MAP[extension](logger, filepath=filepath)
            self.assert_example_data(data)
            assert logger.log == [], logger.log
        
    def test_1_example_file_by_buf(self):
        for extension in EXTENSIONS:
            logger = BasicLogger()
            filepath = examples.get_spreadsheet_filepath(EXAMPLE_TESTFILE_SUFFIX, extension)
            f = open(filepath, 'rb')
            buf = f.read()
            f.close()
            data = SPREADSHEET_DATA_MAP[extension](logger, buf=buf)
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

class TestDataRecords:
    def test_0_example(self):
        data = examples.get_data(EXAMPLE_TESTFILE_SUFFIX, XL_EXTENSION)
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

    def test_1_bis_example(self):
        data = examples.get_data(EXAMPLE_BIS_TESTFILE_SUFFIX, XL_EXTENSION)
        data_records = spreadsheet_importer.SpreadsheetDataRecords(data, 'Dataset Ref#')
        assert data_records.titles[:3] == [None, 'Dataset Ref#', 'Dataset Status'], data_records.titles
        records = [record for record in data_records.records]
        assert len(records) == 2, records
        assert records[0]['Dataset Ref#'] == 'BIS-000002', records[0]['Dataset Ref#']
        assert records[1]['Dataset Ref#'] == 'BIS-000003', records[1]['Dataset Ref#']

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
            filepath = examples.get_spreadsheet_filepath(EXAMPLE_TESTFILE_SUFFIX, extension)
            package_import = spreadsheet_importer.SpreadsheetPackageImporter(filepath=filepath)
            self.assert_example_package_import(package_import)

    def assert_example_package_import(self, package_import):
        pkg_dicts = [pkg_dict for pkg_dict in package_import.pkg_dict()]
        assert len(pkg_dicts) == 2, pkg_dicts
        assert pkg_dicts[0].items() == [(u'name', u'wikipedia'), (u'title', u'Wikipedia'), ('resources', [{'url': u'http://static.wikipedia.org/downloads/2008-06/en/wikipedia-en-html.tar.7z', 'hash': u'', 'description': u'In English', 'format': u'html', u'alt_url': u'', u'size':u''}]), (u'tags', u'encyclopedia reference')], pkg_dicts[0].items()
        assert pkg_dicts[1].items() == [(u'name', u'tviv'), (u'title', u'TV IV'), ('resources', [{'url': u'http://tviv.org/Category:Grids', 'hash': u'', 'description': u'', 'format': u'', u'alt_url': u'', u'size':u''}]), (u'tags', u'tv encyclopedia')], pkg_dicts[1].items()        
