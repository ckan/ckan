from contextlib import contextmanager
from email.utils import encode_rfc2231
import json

import unicodecsv

UTF8_BOM = u'\uFEFF'.encode('utf-8')


@contextmanager
def csv_writer(response, columns, name=None, bom=False):
    u'''Context manager for writing UTF-8 CSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param columns: list of column names
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with csv_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, 'headers'):
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        if name:
            response.headers['Content-disposition'] = (
                'attachment; filename="{name}.csv"'.format(
                    name=encode_rfc2231(name)))
    wr = unicodecsv.writer(response, encoding='utf-8')
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(columns)
    yield wr


@contextmanager
def tsv_writer(response, columns, name=None, bom=False):
    u'''Context manager for writing UTF-8 TSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param columns: list of column names
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with tsv_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, 'headers'):
        response.headers['Content-Type'] = (
            'text/tab-separated-values; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                'attachment; filename="{name}.tsv"'.format(
                    name=encode_rfc2231(name)))
    wr = unicodecsv.writer(
        response, encoding='utf-8', dialect=unicodecsv.excel_tab)
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(columns)
    yield wr


@contextmanager
def json_writer(response, columns, name=None, bom=False):
    u'''Context manager for writing UTF-8 JSON data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param columns: list of column names
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with json_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, 'headers'):
        response.headers['Content-Type'] = (
            'application/json; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                'attachment; filename="{name}.json"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(UTF8_BOM)
    response.write(b'{\n  "data": [')
    yield JSONWriter(response, columns)
    response.write(b'\n]}\n')


class JSONWriter(object):
    def __init__(self, response, columns):
        self.response = response
        self.columns = columns
        self.first = True

    def writerow(self, row):
        if self.first:
            self.first = False
            self.response.write(b'\n    ')
        else:
            self.response.write(b',\n    ')
        self.response.write(json.dumps(
            {k: v for (k, v) in zip(self.columns, row)},
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True).encode('utf-8'))
