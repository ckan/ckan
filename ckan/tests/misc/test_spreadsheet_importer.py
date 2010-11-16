import types
import tempfile
import os

from sqlalchemy.util import OrderedDict

import ckan.model as model
from ckan.tests import *
import ckan.lib.importer as importer
import ckan.lib.spreadsheet_importer as spreadsheet_importer
import ckan.lib.dumper as dumper
from pylons import config

TEST_FILES_DIR = os.path.join(config['here'], 'ckan/tests/misc/')
TEST_FILE_FULL = 'test_importer_full'
TEST_FILE_EXAMPLE = 'test_importer_example'
XL_EXTENSION = '.xls'
CSV_EXTENSION = '.csv'
EXTENSIONS = [XL_EXTENSION, CSV_EXTENSION]

EXAMPLE_XL_DICTS = [
    OrderedDict(
        [('name', 'wikipedia'),
         ('title', 'Wikipedia'),
         ('resource-0-url', 'http://static.wikipedia.org/downloads/2008-06/en/wikipedia-en-html.tar.7z'),
         ('resource-0-format', 'html'),
         ('resource-0-description', 'In English'),
         ('tags', 'encyclopedia reference')]),
    OrderedDict(
        [('name', 'tviv'),
         ('title', 'TV IV'),
         ('resource-0-url', 'http://tviv.org/Category:Grids'),
         ('tags', 'tv encyclopedia')]),
    ]

pkg_to_xl_dict = dumper.PackagesXlWriter.pkg_to_xl_dict

# TO RECREATE TEST FILES, uncomment this test
class Test0FilesCreation(TestController):
    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()
        full_row_dicts = [pkg_to_xl_dict(pkg) for pkg in [model.Package.by_name(u'annakarenina'), model.Package.by_name(u'warandpeace')]]
        creators = [ (dumper.PackagesXlWriter, XL_EXTENSION),
                     (dumper.PackagesCsvWriter, CSV_EXTENSION),
                     ]
        for creator, extension in creators:
            creator(full_row_dicts).save(open(TEST_FILES_DIR + TEST_FILE_FULL + extension, 'wb'))
            creator(EXAMPLE_XL_DICTS).save(open(TEST_FILES_DIR + TEST_FILE_EXAMPLE + extension, 'wb'))

    def test_exist(self):
        for filename in (TEST_FILE_EXAMPLE, TEST_FILE_FULL):
            for extension in EXTENSIONS:
                filepath = TEST_FILES_DIR + filename + extension
                assert os.path.exists(filepath), filepath

class Test1Import(TestController):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        CreateTestData.create()
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        self.anna_xl_dict = pkg_to_xl_dict(anna)
        self.war_xl_dict = pkg_to_xl_dict(war)
        self.anna_fs_dict = pkg_to_fs_dict(anna)
        self.war_fs_dict = pkg_to_fs_dict(war)
        self.full_buf = {} # extension:filebuf
        for extension in EXTENSIONS:
            filepath = TEST_FILES_DIR + TEST_FILE_FULL + XL_EXTENSION
            assert os.path.exists(filepath)
            f = open(filepath)
            self.full_buf[extension] = f.read()
            f.close()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def _get_row(self, sheet, row_index):
        return [cell.value for cell in sheet.row(row_index)]

    def test_0_pkg_to_xl_dict(self):
        d = self.anna_xl_dict
        for key, value in d.items():
            assert isinstance(d[key], (str, unicode, types.NoneType)), '%s:%s %s' % (key, value, type(value))
        for key in ['name', 'license', 'tags', 'groups', 'genre']:
            assert d.has_key(key), key
        for key in ['id', 'license_id', 'ratings_average', 'extras']:
            assert not d.has_key(key), key

    def test_1_pkg_to_fs_dict(self):
        d = self.anna_fs_dict
        for key, value in d.items():
            if key == 'extras':
                assert isinstance(d[key], dict), '%s:%s %s' % (key, value, type(value))                
            elif key == 'resources':
                assert isinstance(d[key], list), '%s:%s %s' % (key, value, type(value))
                # check each resource
                for value in d[key]:
                    assert isinstance(value, dict), '%s %s' % (value, type(value))
            else:
                assert isinstance(d[key], (str, unicode, types.NoneType)), '%s:%s %s' % (key, value, type(value))
        for key in ['name', 'license_id', 'tags', 'groups', 'extras']:
            assert d.has_key(key), '%s not in %s' % (key, d)
        for key in ['id', 'license', 'ratings_average', 'genre', 'ckan_url']:
            assert not d.has_key(key), key

    def test_2_creator_xl_file(self):
        import xlrd
        assert self.full_buf[XL_EXTENSION]
        
        book = xlrd.open_workbook(file_contents=self.full_buf[XL_EXTENSION])
        assert book.nsheets == 1, book.nsheets
        sheet = book.sheet_by_index(0)
        titles = self._get_row(sheet, 0)
        assert titles[:2] == ['name', 'title'], titles
        row1 = self._get_row(sheet, 1)
        assert row1[:2] == ['annakarenina', 'A Novel By Tolstoy'], row1
        row2 = self._get_row(sheet, 2)
        assert row2[:2] == ['warandpeace', 'A Wonderful Story'], row2

    def test_3_read_full_buf(self):
        comparison_dicts = [self.anna_fs_dict, self.war_fs_dict]
        for extension in EXTENSIONS:
            log = self._test_read(buf=self.full_buf[extension], expected_dicts=comparison_dicts)
            assert not log, log

    def test_3_read_full_file(self):
        comparison_dicts = [self.anna_fs_dict, self.war_fs_dict]
        for extension in EXTENSIONS:
            filepath = TEST_FILES_DIR + TEST_FILE_FULL + extension
            log = self._test_read(filepath=filepath, expected_dicts=comparison_dicts)
            assert not log, log

    def test_4_read_example_file(self):
        comparison_dicts = [pkg_xl_dict_to_fs_dict(xl_dict) for xl_dict in EXAMPLE_XL_DICTS]
        for extension in EXTENSIONS:
            log = self._test_read(filepath=TEST_FILES_DIR + TEST_FILE_EXAMPLE + extension, expected_dicts=comparison_dicts)

    def _test_read(self, buf=None, filepath=None, expected_dicts=None):
        reader = spreadsheet_importer.SpreadsheetPackageImporter(buf=buf, filepath=filepath)
        index = 0
        for pkg_dict in reader.pkg_dict():
            for key, comp_val in expected_dicts[index].items():
                err_msg = 'Package \'%s\', Key %s should be: \n%s' % (pkg_dict['name'], repr(key), repr(comp_val))
                if comp_val:
                    assert pkg_dict.has_key(key), err_msg
                    err_msg += ', but is: \n%s' % (repr(pkg_dict[key]))
                    if key in ('groups', 'tags'):
                        #order doesn't matter
                        a = set(); b = set()
                        [a.add(val) for val in pkg_dict[key].split(' ')]
                        [b.add(val) for val in comp_val.split(' ')]
                        assert a == b, err_msg
                    elif key == 'license_id':
                        assert pkg_dict[key] == str(comp_val), err_msg
                    else:
                        assert pkg_dict[key] == comp_val, err_msg
                else:
                    assert not pkg_dict.has_key(key), err_msg
            for key, val in pkg_dict.items():
                comp_val = expected_dicts[index].get(key, None)
                assert not (val and not comp_val), 'Package \'%s\', Key \'%s\' with value \'%s\' appeared.' % (pkg_dict['name'], key, val)

            index += 1
        return reader.get_log()

# TODO: (rgrp: 2010-11-16)
# why is not in the ckan/lib/spreadsheet_importer.pkg_xl_dict_to_fs_dict(cls, # pkg_xl_dict, logger=None)?
# furthermore why is that not in a core module (or forms) rather than there ...
def pkg_to_fs_dict(pkg):
    '''Convert a Package object to a dictionary suitable for fieldset data.
    e.g. {'name':'annakarenina', 'resources':{'url':'anna.com'}}'''
    dict_ = pkg.as_dict()
    for key, value in dict_.items():
        if (key.endswith('_id') and key != 'license_id') or key.startswith('rating') or key == 'id':
            del dict_[key]
        if key=='resources':
            dict_[key] = [res.as_dict(core_columns_only=True) for res in pkg.resources]
        elif isinstance(value, (list, tuple)):
            dict_[key] = ' '.join(value)
        elif key in ('license', 'ckan_url'):
            del dict_[key]
        elif key in ['metadata_modified', 'metadata_created']:
            del dict_[key]
    return dict_

def pkg_xl_dict_to_fs_dict(pkg_xl_dict):
    return spreadsheet_importer.SpreadsheetPackageImporter.pkg_xl_dict_to_fs_dict(pkg_xl_dict)
