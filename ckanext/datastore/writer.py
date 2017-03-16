# encoding: utf-8

from contextlib import contextmanager
from email.utils import encode_rfc2231
import json
from xml.etree.cElementTree import Element, SubElement, ElementTree

import unicodecsv

UTF8_BOM = u'\uFEFF'.encode(u'utf-8')


def _json_dump_nested(value):
    is_nested = isinstance(value, (list, dict))

    if is_nested:
        return json.dumps(value)
    return value


@contextmanager
def csv_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 CSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with csv_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = b'text/csv; charset=utf-8'
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.csv"'.format(
                    name=encode_rfc2231(name)))
    wr = CSVWriter(response, fields, encoding=u'utf-8')
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(f['id'] for f in fields)
    yield wr


@contextmanager
def tsv_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 TSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with tsv_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'text/tab-separated-values; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.tsv"'.format(
                    name=encode_rfc2231(name)))
    wr = CSVWriter(
        response, fields, encoding=u'utf-8', dialect=unicodecsv.excel_tab,
    )
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(f['id'] for f in fields)
    yield wr


class CSVWriter(object):
    def __init__(self, response, columns, *args, **kwargs):
        self._wr = unicodecsv.writer(response, *args, **kwargs)
        self.columns = columns

    def writerow(self, row):
        return self._wr.writerow([
            _json_dump_nested(val) for val in row])


@contextmanager
def json_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 JSON data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with json_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'application/json; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.json"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(UTF8_BOM)
    response.write(
        b'{\n  "fields": %s,\n  "records": [' % json.dumps(
            fields, ensure_ascii=False, separators=(u',', u':')))
    yield JSONWriter(response, [f['id'] for f in fields])
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
            row,
            ensure_ascii=False,
            separators=(u',', u':'),
            sort_keys=True).encode(u'utf-8'))


@contextmanager
def xml_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 XML data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file

    >>> with xml_writer(response, fields) as d:
    >>>    d.writerow(row1)
    >>>    d.writerow(row2)
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'text/xml; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.xml"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(UTF8_BOM)
    response.write(b'<data>\n')
    yield XMLWriter(response, [f['id'] for f in fields])
    response.write(b'</data>\n')


class XMLWriter(object):
    _key_attr = u'key'
    _value_tag = u'value'

    def __init__(self, response, columns):
        self.response = response
        self.id_col = columns[0] == u'_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def _insert_node(self, root, k, v, key_attr=None):
        element = SubElement(root, k)
        if v is None:
            element.attrib[u'xsi:nil'] = u'true'
        elif not isinstance(v, (list, dict)):
            element.text = unicode(v)
        else:
            if isinstance(v, list):
                it = enumerate(v)
            else:
                it = v.items()
            for key, value in it:
                self._insert_node(element, self._value_tag, value, key)

        if key_attr is not None:
            element.attrib[self._key_attr] = unicode(key_attr)

    def writerow(self, row):
        root = Element(u'row')
        if self.id_col:
            root.attrib[u'_id'] = unicode(row[0])
            row = row[1:]
        for k, v in zip(self.columns, row):
            self._insert_node(root, k, v)
        ElementTree(root).write(self.response, encoding=u'utf-8')
        self.response.write(b'\n')
