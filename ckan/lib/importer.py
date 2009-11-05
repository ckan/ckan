import StringIO

import xlrd
import csv

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
        return self._rows[row_index]

    def get_num_rows(self):
        return self._num_rows

class XlData:
    def __init__(self, logger, filepath=None, buf=None):
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
                        cell = unicode(cell)
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

class CsvPackagesCreator:
    def __init__(self, row_dicts=None):
        self._rows = []
        self._col_titles = []
        titles_set = set()
        for row_dict in row_dicts:
            for key in row_dict.keys():
                titles_set.add(key)
        self._col_titles = list(titles_set)
        for row_dict in row_dicts:
            self._add_row_dict(row_dict)
        
    def _add_row_dict(self, row_dict):
        row = []
        for title in self._col_titles:
            if row_dict.has_key(title):
                row.append(row_dict[title])
            else:
                row.append(None)
        self._rows.append(row)

    def save(self, filepath):
        f = open(filepath, 'wb')
        writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(self._col_titles)
        for row in self._rows:
            writer.writerow(row)

class XlPackagesCreator:
    def __init__(self, row_dicts=None):
        import xlwt
        self._workbook = xlwt.Workbook()
        self._sheet = self._workbook.add_sheet('test')
        self._col_titles = {} # title:col_index
        self._row = 1
        self.add_col_titles(['name', 'title'])
        if row_dicts:
            for row_dict in row_dicts:
                self.add_row_dict(row_dict)
                self._row += 1

    def add_row_dict(self, row_dict):
        for key, value in row_dict.items():
            if value is not None:
                if key not in self._col_titles.keys():
                    self._add_col_title(key)
                col_index = self._col_titles[key]
                self._sheet.write(self._row, col_index, value)

    def get_serialized(self):
        strm = StringIO.StringIO()
        self._workbook.save(strm)
        workbook_serialized = strm.getvalue()
        strm.close()
        return workbook_serialized

    def save(self, filepath):
        self._workbook.save(filepath)

    def add_col_titles(self, titles):
        # use initially to specify the order of column titles
        for title in titles:
            self._add_col_title(title)
                    
    def _add_col_title(self, title):
        if self._col_titles.has_key(title):
            return
        col_index = len(self._col_titles)
        self._sheet.write(0, col_index, title)
        self._col_titles[title] = col_index
