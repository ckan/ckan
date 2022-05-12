# encoding: utf-8
from __future__ import annotations

from contextlib import contextmanager
from email.utils import encode_rfc2231
from typing import Any, Optional
from simplejson import dumps
import six

from xml.etree.cElementTree import Element, SubElement, ElementTree

import csv

from codecs import BOM_UTF8


@contextmanager
def csv_writer(response: Any, fields: list[dict[str, Any]],
               name: Optional[str] = None, bom: bool = False):
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
                u'attachment; filename="{name}.csv"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.stream.write(BOM_UTF8)

    csv.writer(response.stream).writerow(
        f['id'] for f in fields)
    yield TextWriter(response.stream)


@contextmanager
def tsv_writer(response: Any, fields: list[dict[str, Any]],
               name: Optional[str] = None, bom: bool = False):
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
                u'attachment; filename="{name}.tsv"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.stream.write(BOM_UTF8)

    csv.writer(
        response.stream,
        dialect='excel-tab').writerow(
            f['id'] for f in fields)
    yield TextWriter(response.stream)


class TextWriter(object):
    u'text in, text out'
    def __init__(self, response: Any):
        self.response = response

    def write_records(self, records: list[Any]):
        self.response.write(records)


@contextmanager
def json_writer(response: Any, fields: list[dict[str, Any]],
                name: Optional[str] = None, bom: bool = False):
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
                u'attachment; filename="{name}.json"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.stream.write(BOM_UTF8)
    response.stream.write(
        six.ensure_binary(u'{\n  "fields": %s,\n  "records": [' % dumps(
            fields, ensure_ascii=False, separators=(u',', u':'))))
    yield JSONWriter(response.stream)
    response.stream.write(b'\n]}\n')


class JSONWriter(object):
    def __init__(self, response: Any):
        self.response = response
        self.first = True

    def write_records(self, records: list[Any]):
        for r in records:
            if self.first:
                self.first = False
                self.response.write(b'\n    ')
            else:
                self.response.write(b',\n    ')

            self.response.write(dumps(
                r, ensure_ascii=False, separators=(u',', u':')))


@contextmanager
def xml_writer(response: Any, fields: list[dict[str, Any]],
               name: Optional[str] = None, bom: bool = False):
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
                u'attachment; filename="{name}.xml"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.stream.write(BOM_UTF8)
    response.stream.write(b'<data>\n')
    yield XMLWriter(response.stream, [f[u'id'] for f in fields])
    response.stream.write(b'</data>\n')


class XMLWriter(object):
    _key_attr = u'key'
    _value_tag = u'value'

    def __init__(self, response: Any, columns: list[str]):
        self.response = response
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
            ElementTree(root).write(self.response, encoding=u'utf-8')
            self.response.write(b'\n')
