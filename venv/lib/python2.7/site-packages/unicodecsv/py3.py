# -*- coding: utf-8 -*-
import csv
from csv import *


class _UnicodeWriteWrapper(object):
    """Simple write() wrapper that converts unicode to bytes."""

    def __init__(self, binary, encoding, errors):
        self.binary = binary
        self.encoding = encoding
        self.errors = errors

    def write(self, string):
        return self.binary.write(string.encode(self.encoding, self.errors))


class UnicodeWriter(object):
    def __init__(self, f, dialect=csv.excel, encoding='utf-8', errors='strict',
                 *args, **kwds):
        if f is None:
            raise TypeError

        f = _UnicodeWriteWrapper(f, encoding=encoding, errors=errors)
        self.writer = csv.writer(f, dialect, *args, **kwds)

    def writerow(self, row):
        return self.writer.writerow(row)

    def writerows(self, rows):
        return self.writer.writerows(rows)

    @property
    def dialect(self):
        return self.writer.dialect


class UnicodeReader(object):
    def __init__(self, f, dialect=None, encoding='utf-8', errors='strict',
                 **kwds):

        format_params = ['delimiter', 'doublequote', 'escapechar',
                     'lineterminator', 'quotechar', 'quoting',
                     'skipinitialspace']

        if dialect is None:
            if not any([kwd_name in format_params
                        for kwd_name in kwds.keys()]):
                dialect = csv.excel

        f = (bs.decode(encoding, errors=errors) for bs in f)
        self.reader = csv.reader(f, dialect, **kwds)

    def __next__(self):
        return self.reader.__next__()

    def __iter__(self):
        return self

    @property
    def dialect(self):
        return self.reader.dialect

    @property
    def line_num(self):
        return self.reader.line_num


writer = UnicodeWriter
reader = UnicodeReader


class DictWriter(csv.DictWriter):
    def __init__(self, csvfile, fieldnames, restval='',
                 extrasaction='raise', dialect='excel', encoding='utf-8',
                 errors='strict', *args, **kwds):
        super().__init__(csvfile, fieldnames, restval,
                         extrasaction, dialect, *args, **kwds)
        self.writer = UnicodeWriter(csvfile, dialect, encoding=encoding,
                                    errors=errors, *args, **kwds)
        self.encoding_errors = errors

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)


class DictReader(csv.DictReader):
    def __init__(self, csvfile, fieldnames=None, restkey=None, restval=None,
                 dialect='excel', encoding='utf-8', errors='strict', *args,
                 **kwds):
        csv.DictReader.__init__(self, csvfile, fieldnames, restkey, restval,
                                dialect, *args, **kwds)
        self.reader = UnicodeReader(csvfile, dialect, encoding=encoding,
                                    errors=errors, *args, **kwds)
