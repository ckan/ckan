# encoding: utf-8
from __future__ import annotations

from io import StringIO, BytesIO

from contextlib import contextmanager
from typing import Any, Optional
from simplejson import dumps

from xml.etree.cElementTree import Element, SubElement, ElementTree

import csv

from codecs import BOM_UTF8


BOM = "\N{bom}"


@contextmanager
def csv_writer(fields: list[dict[str, Any]], bom: bool = False):
    '''Context manager for writing UTF-8 CSV data to file

    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''
    output = StringIO()

    if bom:
        output.write(BOM)

    csv.writer(output).writerow(
        f['id'] for f in fields)
    yield TextWriter(output)


@contextmanager
def tsv_writer(fields: list[dict[str, Any]], bom: bool = False):
    '''Context manager for writing UTF-8 TSV data to file

    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''
    output = StringIO()

    if bom:
        output.write(BOM)

    csv.writer(
        output,
        dialect='excel-tab').writerow(
            f['id'] for f in fields)
    yield TextWriter(output)


class TextWriter(object):
    u'text in, text out'
    def __init__(self, output: StringIO):
        self.output = output

    def write_records(self, records: list[Any]) -> bytes:
        self.output.write(records)  # type: ignore
        self.output.seek(0)
        output = self.output.read().encode('utf-8')
        self.output.truncate(0)
        self.output.seek(0)
        return output

    def end_file(self) -> bytes:
        return b''


@contextmanager
def json_writer(fields: list[dict[str, Any]], bom: bool = False):
    '''Context manager for writing UTF-8 JSON data to file

    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''
    output = StringIO()

    if bom:
        output.write(BOM)

    output.write(
        '{\n  "fields": %s,\n  "records": [' % dumps(
            fields, ensure_ascii=False, separators=(u',', u':')))
    yield JSONWriter(output)


class JSONWriter(object):
    def __init__(self, output: StringIO):
        self.output = output
        self.first = True

    def write_records(self, records: list[Any]) -> bytes:
        for r in records:
            if self.first:
                self.first = False
                self.output.write('\n    ')
            else:
                self.output.write(',\n    ')

            self.output.write(dumps(
                r, ensure_ascii=False, separators=(',', ':')))

        self.output.seek(0)
        output = self.output.read().encode('utf-8')
        self.output.truncate(0)
        self.output.seek(0)
        return output

    def end_file(self) -> bytes:
        return b'\n]}\n'


@contextmanager
def xml_writer(fields: list[dict[str, Any]], bom: bool = False):
    '''Context manager for writing UTF-8 XML data to file

    :param fields: list of datastore fields
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''
    output = BytesIO()

    if bom:
        output.write(BOM_UTF8)

    output.write(
        b'<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
    yield XMLWriter(output, [f[u'id'] for f in fields])


class XMLWriter(object):
    _key_attr = 'key'
    _value_tag = 'value'

    def __init__(self, output: BytesIO, columns: list[str]):
        self.output = output
        self.id_col = columns[0] == '_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def _insert_node(self, root: Any, k: str, v: Any,
                     key_attr: Optional[Any] = None):
        element = SubElement(root, k)
        if v is None:
            element.attrib['xsi:nil'] = 'true'
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

    def write_records(self, records: list[Any]) -> bytes:
        for r in records:
            root = Element('row')
            if self.id_col:
                root.attrib['_id'] = str(r['_id'])
            for c in self.columns:
                self._insert_node(root, c, r[c])
            ElementTree(root).write(self.output, encoding='utf-8')
            self.output.write(b'\n')
        self.output.seek(0)
        output = self.output.read()
        self.output.truncate(0)
        self.output.seek(0)
        return output

    def end_file(self) -> bytes:
        return b'</data>\n'
