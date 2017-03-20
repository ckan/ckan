# encoding: utf-8

from contextlib import contextmanager
from email.utils import encode_rfc2231
import json
from xml.etree.cElementTree import Element, SubElement, ElementTree

import unicodecsv

UTF8_BOM = u'\uFEFF'.encode(u'utf-8')
# Element names can contain letters, digits, hyphens, underscores, and periods
SPECIAL_CHARS = u'#$%&!?\/@}{[]'


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
    wr = unicodecsv.writer(response, encoding=u'utf-8')
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
    wr = unicodecsv.writer(
        response, encoding=u'utf-8', dialect=unicodecsv.excel_tab)
    if bom:
        response.write(UTF8_BOM)
    wr.writerow(f['id'] for f in fields)
    yield wr


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
    def __init__(self, response, columns):
        self.response = response
        self.id_col = columns[0] == u'_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def writerow(self, row):
        root = Element(u'row')
        if self.id_col:
            root.attrib[u'_id'] = unicode(row[0])
            row = row[1:]
        for k, v in zip(self.columns, row):
            k = get_xml_element(k)
            if v is None:
                SubElement(root, k).attrib[u'xsi:nil'] = u'true'
                continue
            SubElement(root, k).text = unicode(v)
        ElementTree(root).write(self.response, encoding=u'utf-8')
        self.response.write(b'\n')


def get_xml_element(element_name):
    u'''Return element name according XML naming standards
        Capitalize every word and remove special characters
       '''
    clean_word = u''.join(c.strip(SPECIAL_CHARS) for c in element_name)
    if unicode(clean_word).isnumeric():
        return u'_' + unicode(element_name)
    first, rest = clean_word.split(u' ')[0], clean_word.split(u' ')[1:]
    return first + u''.join(w.capitalize()for w in rest)
