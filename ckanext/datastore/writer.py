# encoding: utf-8
from __future__ import annotations

from io import StringIO

from contextlib import contextmanager
from typing import Any, Optional
from simplejson import dumps

from xml.etree.cElementTree import Element, SubElement, ElementTree

import csv

from codecs import BOM_UTF8


@contextmanager
def csv_writer(output: StringIO, fields: list[dict[str, Any]],
               bom: bool = False):
    u'''Context manager for writing UTF-8 CSV data to file

    :param response: file-like object for writing data
    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if bom:
        output.write(BOM_UTF8.decode())

    csv.writer(output).writerow(
        f['id'].encode('utf-8') for f in fields)
    yield TextWriter(output)


@contextmanager
def tsv_writer(output: StringIO, fields: list[dict[str, Any]],
               bom: bool = False):
    u'''Context manager for writing UTF-8 TSV data to file

    :param response: file-like object for writing data
    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if bom:
        output.write(BOM_UTF8.decode())

    csv.writer(
        output,
        dialect='excel-tab').writerow(
            f['id'].encode('utf-8') for f in fields)
    yield TextWriter(output)


class TextWriter(object):
    u'text in, text out'
    def __init__(self, output: StringIO):
        self.output = output

    def write_records(self, records: list[Any]):
        self.output.write([r.encode('utf-8') for r in records])


@contextmanager
def json_writer(output: StringIO, fields: list[dict[str, Any]],
                bom: bool = False):
    u'''Context manager for writing UTF-8 JSON data to file

    :param response: file-like object for writing data
    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if bom:
        output.write(BOM_UTF8.decode())
    output.write(
        '{\n  "fields": %s,\n  "records": [' % dumps(
            fields, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    yield JSONWriter(output)
    output.write('\n]}\n')


class JSONWriter(object):
    def __init__(self, output: StringIO):
        self.output = output
        self.first = True

    def write_records(self, records: list[Any]):
        for r in records:
            if self.first:
                self.first = False
                self.output.write('\n    ')
            else:
                self.output.write(',\n    ')

            self.output.write(dumps(
                r, ensure_ascii=False, separators=(u',', u':'))
                .encode('utf-8'))


@contextmanager
def xml_writer(output: StringIO, fields: list[dict[str, Any]],
               bom: bool = False):
    u'''Context manager for writing UTF-8 XML data to file

    :param response: file-like object for writing data
    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if bom:
        output.write(BOM_UTF8.decode())
    output.write(
        '<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
    yield XMLWriter(output, [f['id'].encode('utf-8') for f in fields])
    output.write('</data>\n')


class XMLWriter(object):
    _key_attr = u'key'
    _value_tag = u'value'

    def __init__(self, output: StringIO, columns: list[str]):
        self.output = output
        self.id_col = columns[0] == u'_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def _insert_node(self, root: Any, k: str, v: Any,
                     key_attr: Optional[Any] = None):
        element = SubElement(root, k)
        if v is None:
            element.attrib[u'xsi:nil'] = u'true'
        elif not isinstance(v, (list, dict)):
            element.text = str(v)
        else:
            if isinstance(v, list):
                it = enumerate(v)
            else:
                it = v.items()
            for key, value in it:
                self._insert_node(element, self._value_tag, value, key)

        if key_attr is not None:
            element.attrib[self._key_attr] = str(key_attr)

    def write_records(self, records: list[Any]):
        for r in records:
            root = Element(u'row')
            if self.id_col:
                root.attrib[u'_id'] = str(r[u'_id'])
            for c in self.columns:
                self._insert_node(root, c, r[c])
            ElementTree(root).write(self.output, encoding=u'utf-8')
            self.output.write(b'\n')
