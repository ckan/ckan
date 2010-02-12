import StringIO

import csv
import re

import ckan.model as model

class ImportException(Exception):
    pass

class CsvData:
    def __init__(self, logger, filepath=None, buf=None):
        assert filepath or buf
        assert not (filepath and buf)
        self._logger = logger
        self._rows = []
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

class XlData:
    def __init__(self, logger, filepath=None, buf=None):
        import xlrd

        assert filepath or buf
        assert not (filepath and buf)
        self._logger = logger

        try:
            if filepath:
                self._book = xlrd.open_workbook(filepath)
            elif buf:
                self._book = xlrd.open_workbook(file_contents=buf)
        except xlrd.XLRDError, e:
            raise ImportException('Could not open workbook: %r' % e)

        self.sheet = self._book.sheet_by_index(0)
        if self._book.nsheets != 1:
            self._logger('Warning: Just importing from sheet %r' % self.sheet.name)

    def get_row(self, row_index):
        row = self.sheet.row(row_index)
        row_values = [cell.value for cell in row]
        return row_values

    def get_num_rows(self):
        return self.sheet.nrows

class PackageImporter:
    def __init__(self, filepath=None, buf=None):
        self._log = []
        try:
            self._data = XlData(self.log, filepath=filepath, buf=buf)
        except ImportException, e:
            # try csv
            self._data = CsvData(self.log, filepath=filepath, buf=buf)
        import ckan.forms
        self._standard_fields = [key.split('-')[-1] for key in ckan.forms.get_package_dict().keys()]

        self._row_index = -1
        self._titles = []
        while 'title' not in self._titles and 'Title' not in self._titles and 'name' not in self._titles and 'Name' not in self._titles:
            if self._titles is None:
                raise 'No titles'
            self._row_index += 1
            if self._row_index >= self._data.get_num_rows():
                raise ImportException('Could not find title row')
            self._titles = self._data.get_row(self._row_index)
        self._titles = [title.lower() for title in self._titles]

        
    def pkg_dict(self):
        '''Iterator for the package dicts'''
        row = []
        for row_index in range(self._data.get_num_rows())[self._row_index+1:]:
            row = self._data.get_row(row_index)
            if row:
                pkg_dict = {}
                for col_index, cell in enumerate(row):
                    if cell:
                        title = self._titles[col_index]
                        if not title:
                            self._log.append('Warning: No title for column %i. Titles: %s' % (col_index, ', '.join(self._titles)))
                        else:
                            if title in self._standard_fields:
                                pkg_dict[title] = cell
                            elif title == 'license':
                                license = model.License.by_name(cell)
                                if license:
                                    pkg_dict['license_id'] = '%s' % license.id
                                else:
                                    self._log.append('Warning: No license name matches \'%s\'. Ignoring license.' % cell)
                            elif title.startswith('resource-'):
                                match = re.match('resource-(\d+)-(\w+)', title)
                                if match:
                                    res_index, field = match.groups()
                                    res_index = int(res_index)
                                    field = str(field)
                                    if not pkg_dict.has_key('resources'):
                                        pkg_dict['resources'] = []
                                    resources = pkg_dict['resources']
                                    num_new_resources = 1 + res_index - len(resources)
                                    for i in range(num_new_resources):
                                        blank_dict = {}
                                        for blank_field in model.PackageResource.get_columns():
                                            blank_dict[blank_field] = u''
                                        pkg_dict['resources'].append(blank_dict)
                                    pkg_dict['resources'][res_index][field] = cell
                                else:
                                    self._log.append('Warning: Could not understand resource title \'%s\'. Ignoring value: %s' % (title, cell))
                            elif title == 'download_url':
                                # deprecated - only in there for compatibility
                                pass
                            else:
                                if not pkg_dict.has_key('extras'):
                                    pkg_dict['extras'] = {}
                                pkg_dict['extras'][title] = cell
                yield pkg_dict
        raise StopIteration

    def log(self, msg):
        self._log.append(msg)

    def get_log(self):
        return self._log

