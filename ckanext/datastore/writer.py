from contextlib import contextmanager

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
                'attachment; filename="{name}.csv"'.format(name=name))
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
            'text/csv;tab-separated-values charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                'attachment; filename="{name}.tsv"'.format(name=name))
    wr = unicodecsv.writer(
        response, encoding='utf-8', dialect=unicodecsv.excel_tab)
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(columns)
    yield wr
