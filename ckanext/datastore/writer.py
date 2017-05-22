# encoding: utf-8

from contextlib import contextmanager
from email.utils import encode_rfc2231
from simplejson import dumps
from xml.etree.cElementTree import Element, SubElement, ElementTree

import unicodecsv

from codecs import BOM_UTF8


@contextmanager
def csv_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 CSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = b'text/csv; charset=utf-8'
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.csv"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(BOM_UTF8)

    unicodecsv.writer(response, encoding=u'utf-8').writerow(
        f['id'] for f in fields)
    yield TextWriter(response)


@contextmanager
def tsv_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 TSV data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'text/tab-separated-values; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.tsv"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(BOM_UTF8)

    unicodecsv.writer(
        response, encoding=u'utf-8', dialect=unicodecsv.excel_tab).writerow(
            f['id'] for f in fields)
    yield TextWriter(response)


class TextWriter(object):
    u'text in, text out'
    def __init__(self, response):
        self.response = response

    def write_records(self, records):
        self.response.write(records)


@contextmanager
def json_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 JSON data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'application/json; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.json"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(BOM_UTF8)
    response.write(
        b'{\n  "fields": %s,\n  "records": [' % dumps(
            fields, ensure_ascii=False, separators=(u',', u':')))
    yield JSONWriter(response)
    response.write(b'\n]}\n')


class JSONWriter(object):
    def __init__(self, response):
        self.response = response
        self.first = True

    def write_records(self, records):
        for r in records:
            if self.first:
                self.first = False
                self.response.write(b'\n    ')
            else:
                self.response.write(b',\n    ')

            self.response.write(dumps(
                r, ensure_ascii=False, separators=(u',', u':')))


@contextmanager
def xml_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 XML data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'text/xml; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.xml"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(BOM_UTF8)
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

    def write_records(self, records):
        for r in records:
            root = Element(u'row')
            if self.id_col:
                root.attrib[u'_id'] = unicode(r[u'_id'])
            for c in self.columns:
                self._insert_node(root, c, r[c])
            ElementTree(root).write(self.response, encoding=u'utf-8')
            self.response.write(b'\n')
