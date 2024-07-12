# encoding: utf-8
import re
from __future__ import annotations

from io import StringIO, BytesIO

from contextlib import contextmanager
from typing import Any, Optional
from simplejson import dumps

from xml.etree.cElementTree import Element, SubElement, ElementTree

import csv

from codecs import BOM_UTF8
import unicodedata


BOM = "\N{bom}"

xml_element_name_rules = [
    # cannot start with XML or number
    (re.compile(r'^(\d*xml\d*|\d+)', re.I), ''),
    # cannot contain spaces
    (re.compile(r'\s+'), '_'),
    # can only contain letters, underscores, stops, and hyphens
    (re.compile(r'[^\w_.-]', re.U), ''),
    # must start with a letter or underscore
    (re.compile(r'^[\d.-]+'), ''),
]


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
    'text in, text out'
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
            fields, ensure_ascii=False, separators=(',', ':')))
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
    yield XMLWriter(output, [f['id'] for f in fields])


class XMLWriter(object):
    _key_attr = 'key'
    _value_tag = 'value'

    def __init__(self, output: BytesIO, columns: list[str]):
        self.output = output
        self.id_col = columns[0] == '_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns
        self.element_names = {}
        for col in columns:
            element_name = unicodedata.normalize('NFC', col)
            for rule, replacement in xml_element_name_rules:
                element_name = re.sub(rule, replacement, element_name)
            unique_suffix = 0
            unique_name = element_name
            while unique_name in self.element_names.values():
                unique_name = '%s_%s' % (element_name, unique_suffix)
                unique_suffix += 1
            self.element_names[col] = unique_name

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
                self._insert_node(root, self.element_names[c], r[c])
            ElementTree(root).write(self.output, encoding='utf-8')
            self.output.write(b'\n')
        self.output.seek(0)
        output = self.output.read()
        self.output.truncate(0)
        self.output.seek(0)
        return output

    def end_file(self) -> bytes:
        return b'</data>\n'
