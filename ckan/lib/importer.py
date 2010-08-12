import StringIO

import csv
import re

from sqlalchemy.util import OrderedDict

from ckan.model.license import LicenseRegister
import ckan.model as model
import ckan.forms

class ImportException(Exception):
    pass


class SpreadsheetData(object):
    '''Represents a spreadsheet file which you can access row by row.''' 
    def __init__(self, logger, filepath=None, buf=None):
        assert filepath or buf
        assert not (filepath and buf)
        self._logger = logger
        self._rows = []

    def get_row(self, row_index):
        'Returns a list of the cells in unicode format.'
        raise NotImplementedError

    def get_num_rows(self):
        'Returns the number of rows in the sheet.'
        raise NotImplementedError

    def get_all_rows(self):
        'A crude way to get all the rows at once.'
        return [self.get_row(i) for i in range(self.get_num_rows())]


class CsvData(SpreadsheetData):
    def __init__(self, logger, filepath=None, buf=None):
        super(CsvData, self).__init__(logger, filepath, buf)
        if 1:
            if filepath:
                csvfile = open(filepath)
                if not csvfile:
                    raise ImportException('Could not open file \'%s\'.' % filepath)
                csv_snippet = csvfile.read(1024)
            elif buf:
                csvfile = buf.split('\n')
                if not csvfile:
                    raise ImportException('Empty csv data.')
                csv_snippet = buf[:1024]

            try:
                dialect = csv.Sniffer().sniff(csv_snippet)
                dialect.doublequote = True # sniff doesn't seem to pick this up
            except csv.Error, inst:
                dialect = None
            if filepath:
                csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)

        try:
            for line in reader:
                self._rows.append(line)
        except csv.Error, inst:
            raise ImportException('CSV file corrupt: %s' % inst)
        self._num_rows = len(self._rows)
        if self._num_rows < 2:
            raise ImportException('Not enough rows')
            
    def get_row(self, row_index):
        row = self._rows[row_index]
        return [cell.decode('utf8') for cell in row]

    def get_num_rows(self):
        return self._num_rows


class XlData(SpreadsheetData):
    '''Spreadsheet data in Excel format.
    NB Cells with no value return None rather than u''.
    '''
    def __init__(self, logger, filepath=None, buf=None, sheet_index=0):
        super(XlData, self).__init__(logger, filepath, buf)
        import xlrd

        try:
            if filepath:
                self._book = xlrd.open_workbook(filepath)
            elif buf:
                self._book = xlrd.open_workbook(file_contents=buf)
        except xlrd.XLRDError, e:
            raise ImportException('Could not open workbook: %r' % e)

        self.sheet = self._book.sheet_by_index(sheet_index)
        if self._book.nsheets != 1:
            self._logger('Warning: Just importing from sheet %r' % self.sheet.name)

    def get_sheet_names(self):
        return self._book.sheet_names()

    def get_row(self, row_index):
        import xlrd
        row = self.sheet.row(row_index)
        row_values = []
        for cell in row:
            value = None
            if cell.ctype == xlrd.XL_CELL_TEXT:
                value = cell.value
            elif cell.ctype == xlrd.XL_CELL_EMPTY:
                value = None
            else:
                raise ImportException, 'Unknown cell type: %s' % cell.ctype
            row_values.append(value)    
        return row_values

    def get_num_rows(self):
        return self.sheet.nrows

class DataRecords(object):
    '''Takes SpreadsheetData and converts it its titles and
    data records. Handles title rows and filters out rows of rubbish.
    '''
    def __init__(self, data, essential_title):
        self._data = data
        # find titles row
        row_index = -1
        self.titles = []
        essential_title_lower = essential_title.lower()
        while essential_title not in self.titles and\
              essential_title.lower() not in self.titles:
            row_index += 1
            if row_index >= self._data.get_num_rows():
                raise ImportException('Could not find title row')
            self.titles = self._data.get_row(row_index)
        self._first_record_row = row_index + 1

    @property
    def records(self):
        '''Returns each record as a dict.'''
        for row_index in range(self._first_record_row, self._data.get_num_rows()):
            row = self._data.get_row(row_index)
            if row:
                record = OrderedDict()
                yield OrderedDict(zip(self.titles, row))
    
class PackageImporter(object):
    '''From a filepath of an Excel or csv file, extracts package
    dictionaries.'''
    def __init__(self, filepath=None, buf=None):
        self._log = []
        self._resources_data = None # BIS data comes with this separate sheet
        try:
            package_data = XlData(self.log, filepath=filepath, buf=buf, sheet_index=0)
            sheet_names = package_data.get_sheet_names()
            if 'Resources' in sheet_names:
                self._resources_data = XlData(self.log, filepath=filepath, buf=buf, sheet_index=sheet_names.index('Resources'))
        except ImportException, e:
            # try csv
            package_data = CsvData(self.log, filepath=filepath, buf=buf)
        import ckan.forms

        self._package_data_records = DataRecords(package_data, 'Title')
        self._resource_data_records =\
                  DataRecords(self._resources_data, 'Resource Title') \
                  if self._resources_data else None
        
    def pkg_dict(self):
        '''Generates package dicts from the package data records.'''
        for row_dict in self._package_data_records.records:
            pkg_dict = self.pkg_xl_dict_to_fs_dict(row_dict, self.log)
            yield pkg_dict
        raise StopIteration

    @classmethod
    def pkg_xl_dict_to_fs_dict(cls, pkg_xl_dict, logger=None):
        '''Convert a Package represented in an Excel-type dictionary to a
        dictionary suitable for fieldset data.
        Takes Excel-type dict:
            {'name':'wikipedia', 
             'resource-0-url':'http://static.wikipedia.org/'}
        Returns Fieldset-type dict:
            {'name':'wikipedia',
             'resources':[{'url':'http://static.wikipedia.org/'}]}
        '''
        standard_fields = [key.split('-')[-1] for key in ckan.forms.get_package_dict().keys()]

        pkg_fs_dict = OrderedDict()
        for title, cell in pkg_xl_dict.items():
            if cell:
                if title in standard_fields:
                    pkg_fs_dict[title] = cell
                elif title == 'license':
                    license = LicenseRegister().get_by_title(cell)
                    if license:
                        pkg_fs_dict['license_id'] = '%s' % license.id
                    else:
                        logger('Warning: No license name matches \'%s\'. Ignoring license.' % cell)
                elif title.startswith('resource-'):
                    match = re.match('resource-(\d+)-(\w+)', title)
                    if match:
                        res_index, field = match.groups()
                        res_index = int(res_index)
                        field = str(field)
                        if not pkg_fs_dict.has_key('resources'):
                            pkg_fs_dict['resources'] = []
                        resources = pkg_fs_dict['resources']
                        num_new_resources = 1 + res_index - len(resources)
                        for i in range(num_new_resources):
                            blank_dict = OrderedDict()
                            for blank_field in model.PackageResource.get_columns():
                                blank_dict[blank_field] = u''
                            pkg_fs_dict['resources'].append(blank_dict)

                        pkg_fs_dict['resources'][res_index][field] = cell
                    else:
                        logger('Warning: Could not understand resource title \'%s\'. Ignoring value: %s' % (title, cell))
                elif title.startswith('relationships'):
                    # TODO
                    pass
                elif title == 'download_url':
                    # deprecated - only in there for compatibility
                    pass
                elif title == 'ckan_url':
                    pass
                else:
                    if not pkg_fs_dict.has_key('extras'):
                        pkg_fs_dict['extras'] = {}
                    pkg_fs_dict['extras'][title] = cell
        return pkg_fs_dict

    def log(self, msg):
        self._log.append(msg)

    def get_log(self):
        return self._log

