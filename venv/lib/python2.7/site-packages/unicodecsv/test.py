# -*- coding: utf-8 -*-
# Copyright (C) 2001,2002 Python Software Foundation
# csv package unit tests

import array
import decimal
import os
import string
import sys
import tempfile
import unittest2 as unittest
from codecs import EncodedFile
from io import BytesIO

import unicodecsv as csv

try:
    # Python 2
    chr = unichr
except:
    pass


# pypy and cpython differ under which exception is raised under some
# circumstances e.g. whether a module is written in C or not.
py_compat_exc = (TypeError, AttributeError)


class Test_Csv(unittest.TestCase):
    """
    Test the underlying C csv parser in ways that are not appropriate
    from the high level interface. Further tests of this nature are done
    in TestDialectRegistry.
    """
    def _test_arg_valid(self, ctor, arg):
        self.assertRaises(py_compat_exc, ctor)
        self.assertRaises(py_compat_exc, ctor, None)
        self.assertRaises(py_compat_exc, ctor, arg, bad_attr=0)
        self.assertRaises(py_compat_exc, ctor, arg, delimiter=0)
        self.assertRaises(py_compat_exc, ctor, arg, delimiter='XX')
        self.assertRaises(csv.Error, ctor, arg, 'foo')
        self.assertRaises(py_compat_exc, ctor, arg, delimiter=None)
        self.assertRaises(py_compat_exc, ctor, arg, delimiter=1)
        self.assertRaises(py_compat_exc, ctor, arg, quotechar=1)
        self.assertRaises(py_compat_exc, ctor, arg, lineterminator=None)
        self.assertRaises(py_compat_exc, ctor, arg, lineterminator=1)
        self.assertRaises(py_compat_exc, ctor, arg, quoting=None)
        self.assertRaises(py_compat_exc, ctor, arg,
                          quoting=csv.QUOTE_ALL, quotechar='')
        self.assertRaises(py_compat_exc, ctor, arg,
                          quoting=csv.QUOTE_ALL, quotechar=None)

    def test_reader_arg_valid(self):
        self._test_arg_valid(csv.reader, [])

    def test_writer_arg_valid(self):
        self._test_arg_valid(csv.writer, BytesIO())

    def _test_default_attrs(self, ctor, *args):
        obj = ctor(*args)
        # Check defaults
        self.assertEqual(obj.dialect.delimiter, ',')
        self.assertEqual(obj.dialect.doublequote, True)
        self.assertEqual(obj.dialect.escapechar, None)
        self.assertEqual(obj.dialect.lineterminator, "\r\n")
        self.assertEqual(obj.dialect.quotechar, '"')
        self.assertEqual(obj.dialect.quoting, csv.QUOTE_MINIMAL)
        self.assertEqual(obj.dialect.skipinitialspace, False)
        self.assertEqual(obj.dialect.strict, False)
        # Try deleting or changing attributes (they are read-only)
        self.assertRaises(py_compat_exc, delattr,
                          obj.dialect, 'delimiter')
        self.assertRaises(py_compat_exc, setattr,
                          obj.dialect, 'delimiter', ':')
        self.assertRaises(py_compat_exc, delattr,
                          obj.dialect, 'quoting')
        self.assertRaises(py_compat_exc, setattr,
                          obj.dialect, 'quoting', None)

    def test_reader_attrs(self):
        self._test_default_attrs(csv.reader, [])

    def test_writer_attrs(self):
        self._test_default_attrs(csv.writer, BytesIO())

    def _test_kw_attrs(self, ctor, *args):
        # Now try with alternate options
        kwargs = dict(delimiter=':', doublequote=False, escapechar='\\',
                      lineterminator='\r', quotechar='*',
                      quoting=csv.QUOTE_NONE, skipinitialspace=True,
                      strict=True)
        obj = ctor(*args, **kwargs)
        self.assertEqual(obj.dialect.delimiter, ':')
        self.assertEqual(obj.dialect.doublequote, False)
        self.assertEqual(obj.dialect.escapechar, '\\')
        self.assertEqual(obj.dialect.lineterminator, "\r")
        self.assertEqual(obj.dialect.quotechar, '*')
        self.assertEqual(obj.dialect.quoting, csv.QUOTE_NONE)
        self.assertEqual(obj.dialect.skipinitialspace, True)
        self.assertEqual(obj.dialect.strict, True)

    def test_reader_kw_attrs(self):
        self._test_kw_attrs(csv.reader, [])

    def test_writer_kw_attrs(self):
        self._test_kw_attrs(csv.writer, BytesIO())

    def _test_dialect_attrs(self, ctor, *args):
        # Now try with dialect-derived options
        class dialect:
            delimiter = '-'
            doublequote = False
            escapechar = '^'
            lineterminator = '$'
            quotechar = '#'
            quoting = csv.QUOTE_ALL
            skipinitialspace = True
            strict = False
        args = args + (dialect,)
        obj = ctor(*args)
        self.assertEqual(obj.dialect.delimiter, '-')
        self.assertEqual(obj.dialect.doublequote, False)
        self.assertEqual(obj.dialect.escapechar, '^')
        self.assertEqual(obj.dialect.lineterminator, "$")
        self.assertEqual(obj.dialect.quotechar, '#')
        self.assertEqual(obj.dialect.quoting, csv.QUOTE_ALL)
        self.assertEqual(obj.dialect.skipinitialspace, True)
        self.assertEqual(obj.dialect.strict, False)

    def test_reader_dialect_attrs(self):
        self._test_dialect_attrs(csv.reader, [])

    def test_writer_dialect_attrs(self):
        self._test_dialect_attrs(csv.writer, BytesIO())

    def _write_test(self, fields, expect, **kwargs):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, **kwargs)
            writer.writerow(fields)
            fileobj.seek(0)
            self.assertEqual(fileobj.read(),
                             expect + writer.dialect.lineterminator.encode('utf-8'))
        finally:
            fileobj.close()
            os.unlink(name)

    def test_write_arg_valid(self):
        import sys
        pypy3 = hasattr(sys, 'pypy_version_info') and sys.version_info.major == 3

        self.assertRaises(TypeError if pypy3 else csv.Error, self._write_test, None, '')
        self._write_test((), b'')
        self._write_test([None], b'""')
        self.assertRaises(csv.Error, self._write_test,
                          [None], None, quoting=csv.QUOTE_NONE)

        # Check that exceptions are passed up the chain
        class BadList:
            def __len__(self):
                return 10

            def __getitem__(self, i):
                if i > 2:
                    raise IOError

        self.assertRaises(IOError, self._write_test, BadList(), '')

        class BadItem:
            def __str__(self):
                raise IOError

        self.assertRaises(IOError, self._write_test, [BadItem()], '')

    def test_write_bigfield(self):
        # This exercises the buffer realloc functionality
        bigstring = 'X' * 50000
        self._write_test([bigstring, bigstring],
                         b','.join([bigstring.encode('utf-8')] * 2))

    def test_write_quoting(self):
        self._write_test(['a', 1, 'p,q'], b'a,1,"p,q"')
        self.assertRaises(csv.Error,
                          self._write_test,
                          ['a', 1, 'p,q'], b'a,1,p,q',
                          quoting=csv.QUOTE_NONE)
        self._write_test(['a', 1, 'p,q'], b'a,1,"p,q"',
                         quoting=csv.QUOTE_MINIMAL)
        self._write_test(['a', 1, 'p,q'], b'"a",1,"p,q"',
                         quoting=csv.QUOTE_NONNUMERIC)
        self._write_test(['a', 1, 'p,q'], b'"a","1","p,q"',
                         quoting=csv.QUOTE_ALL)
        self._write_test(['a\nb', 1], b'"a\nb","1"',
                         quoting=csv.QUOTE_ALL)

    def test_write_decimal(self):
        self._write_test(['a', decimal.Decimal("1.1"), 'p,q'], b'"a",1.1,"p,q"',
                         quoting=csv.QUOTE_NONNUMERIC)

    def test_write_escape(self):
        self._write_test(['a', 1, 'p,q'], b'a,1,"p,q"',
                         escapechar='\\')
        self.assertRaises(csv.Error,
                          self._write_test,
                          ['a', 1, 'p,"q"'], b'a,1,"p,\\"q\\""',
                          escapechar=None, doublequote=False)
        self._write_test(['a', 1, 'p,"q"'], b'a,1,"p,\\"q\\""',
                         escapechar='\\', doublequote=False)
        self._write_test(['"'], b'""""',
                         escapechar='\\', quoting=csv.QUOTE_MINIMAL)
        self._write_test(['"'], b'\\"',
                         escapechar='\\', quoting=csv.QUOTE_MINIMAL,
                         doublequote=False)
        self._write_test(['"'], b'\\"',
                         escapechar='\\', quoting=csv.QUOTE_NONE)
        self._write_test(['a', 1, 'p,q'], b'a,1,p\\,q',
                         escapechar='\\', quoting=csv.QUOTE_NONE)

    def test_writerows(self):
        class BrokenFile:
            def write(self, buf):
                raise IOError

        writer = csv.writer(BrokenFile())
        self.assertRaises(IOError, writer.writerows, [['a']])

        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj)
            self.assertRaises(TypeError, writer.writerows, None)
            writer.writerows([['a', 'b'], ['c', 'd']])
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), b"a,b\r\nc,d\r\n")
        finally:
            fileobj.close()
            os.unlink(name)

    def _read_test(self, input, expect, **kwargs):
        reader = csv.reader(input, **kwargs)
        result = list(reader)
        self.assertEqual(result, expect)

    def test_read_oddinputs(self):
        self._read_test([], [])
        self._read_test([b''], [[]])
        self.assertRaises(csv.Error, self._read_test,
                          [b'"ab"c'], None, strict=1)
        # cannot handle null bytes for the moment
        self.assertRaises(csv.Error, self._read_test,
                          [b'ab\0c'], None, strict=1)
        self._read_test([b'"ab"c'], [['abc']], doublequote=0)

    def test_read_eol(self):
        self._read_test([b'a,b'], [['a', 'b']])
        self._read_test([b'a,b\n'], [['a', 'b']])
        self._read_test([b'a,b\r\n'], [['a', 'b']])
        self._read_test([b'a,b\r'], [['a', 'b']])
        self.assertRaises(csv.Error, self._read_test, [b'a,b\rc,d'], [])
        self.assertRaises(csv.Error, self._read_test, [b'a,b\nc,d'], [])
        self.assertRaises(csv.Error, self._read_test, [b'a,b\r\nc,d'], [])

    def test_read_escape(self):
        self._read_test([b'a,\\b,c'], [['a', 'b', 'c']], escapechar='\\')
        self._read_test([b'a,b\\,c'], [['a', 'b,c']], escapechar='\\')
        self._read_test([b'a,"b\\,c"'], [['a', 'b,c']], escapechar='\\')
        self._read_test([b'a,"b,\\c"'], [['a', 'b,c']], escapechar='\\')
        self._read_test([b'a,"b,c\\""'], [['a', 'b,c"']], escapechar='\\')
        self._read_test([b'a,"b,c"\\'], [['a', 'b,c\\']], escapechar='\\')

    def test_read_quoting(self):
        self._read_test([b'1,",3,",5'], [['1', ',3,', '5']])
        self._read_test([b'1,",3,",5'], [['1', '"', '3', '"', '5']],
                        quotechar=None, escapechar='\\')
        self._read_test([b'1,",3,",5'], [['1', '"', '3', '"', '5']],
                        quoting=csv.QUOTE_NONE, escapechar='\\')
        # will this fail where locale uses comma for decimals?
        self._read_test([b',3,"5",7.3, 9'], [['', 3, '5', 7.3, 9]],
                        quoting=csv.QUOTE_NONNUMERIC)
        self._read_test([b'"a\nb", 7'], [['a\nb', ' 7']])
        self.assertRaises(ValueError, self._read_test,
                          [b'abc,3'], [[]],
                          quoting=csv.QUOTE_NONNUMERIC)

    def test_read_linenum(self):
        for r in (csv.reader([b'line,1', b'line,2', b'line,3']),
                  csv.DictReader([b'line,1', b'line,2', b'line,3'],
                                 fieldnames=['a', 'b', 'c'])):
            self.assertEqual(r.line_num, 0)
            next(r)
            self.assertEqual(r.line_num, 1)
            next(r)
            self.assertEqual(r.line_num, 2)
            next(r)
            self.assertEqual(r.line_num, 3)
            self.assertRaises(StopIteration, next, r)
            self.assertEqual(r.line_num, 3)

    def test_roundtrip_quoteed_newlines(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj)
            self.assertRaises(TypeError, writer.writerows, None)
            rows = [['a\nb', 'b'], ['c', 'x\r\nd']]
            writer.writerows(rows)
            fileobj.seek(0)
            for i, row in enumerate(csv.reader(fileobj)):
                self.assertEqual(row, rows[i])
        finally:
            fileobj.close()
            os.unlink(name)


class TestDialectRegistry(unittest.TestCase):
    def test_registry_badargs(self):
        self.assertRaises(TypeError, csv.list_dialects, None)
        self.assertRaises(TypeError, csv.get_dialect)
        self.assertRaises(csv.Error, csv.get_dialect, None)
        self.assertRaises(csv.Error, csv.get_dialect, "nonesuch")
        self.assertRaises(TypeError, csv.unregister_dialect)
        self.assertRaises(csv.Error, csv.unregister_dialect, None)
        self.assertRaises(csv.Error, csv.unregister_dialect, "nonesuch")
        self.assertRaises(TypeError, csv.register_dialect, None)
        self.assertRaises(TypeError, csv.register_dialect, None, None)
        self.assertRaises(TypeError, csv.register_dialect, "nonesuch", 0, 0)
        self.assertRaises(TypeError, csv.register_dialect, "nonesuch",
                          badargument=None)
        self.assertRaises(TypeError, csv.register_dialect, "nonesuch",
                          quoting=None)
        self.assertRaises(TypeError, csv.register_dialect, [])

    def test_registry(self):
        class myexceltsv(csv.excel):
            delimiter = "\t"
        name = "myexceltsv"
        expected_dialects = csv.list_dialects() + [name]
        expected_dialects.sort()
        csv.register_dialect(name, myexceltsv)
        try:
            self.assertEqual(csv.get_dialect(name).delimiter, '\t')
            got_dialects = csv.list_dialects()
            got_dialects.sort()
            self.assertEqual(expected_dialects, got_dialects)
        finally:
            csv.unregister_dialect(name)

    def test_register_kwargs(self):
        name = 'fedcba'
        csv.register_dialect(name, delimiter=';')
        try:
            self.assertNotEqual(csv.get_dialect(name).delimiter, '\t')
            self.assertEqual(list(csv.reader([b'X;Y;Z'], name)), [[u'X', u'Y', u'Z']])
        finally:
            csv.unregister_dialect(name)

    def test_incomplete_dialect(self):
        class myexceltsv(csv.Dialect):
            delimiter = "\t"
        self.assertRaises(csv.Error, myexceltsv)

    def test_space_dialect(self):
        class space(csv.excel):
            delimiter = " "
            quoting = csv.QUOTE_NONE
            escapechar = "\\"

        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"abc def\nc1ccccc1 benzene\n")
            fileobj.seek(0)
            rdr = csv.reader(fileobj, dialect=space())
            self.assertEqual(next(rdr), ["abc", "def"])
            self.assertEqual(next(rdr), ["c1ccccc1", "benzene"])
        finally:
            fileobj.close()
            os.unlink(name)

    def test_dialect_apply(self):
        class testA(csv.excel):
            delimiter = "\t"

        class testB(csv.excel):
            delimiter = ":"

        class testC(csv.excel):
            delimiter = "|"

        csv.register_dialect('testC', testC)
        try:
            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, "w+b")
            try:
                writer = csv.writer(fileobj)
                writer.writerow([1, 2, 3])
                fileobj.seek(0)
                self.assertEqual(fileobj.read(), b"1,2,3\r\n")
            finally:
                fileobj.close()
                os.unlink(name)

            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, "w+b")
            try:
                writer = csv.writer(fileobj, testA)
                writer.writerow([1, 2, 3])
                fileobj.seek(0)
                self.assertEqual(fileobj.read(), b"1\t2\t3\r\n")
            finally:
                fileobj.close()
                os.unlink(name)

            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, "w+b")
            try:
                writer = csv.writer(fileobj, dialect=testB())
                writer.writerow([1, 2, 3])
                fileobj.seek(0)
                self.assertEqual(fileobj.read(), b"1:2:3\r\n")
            finally:
                fileobj.close()
                os.unlink(name)

            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, "w+b")
            try:
                writer = csv.writer(fileobj, dialect='testC')
                writer.writerow([1, 2, 3])
                fileobj.seek(0)
                self.assertEqual(fileobj.read(), b"1|2|3\r\n")
            finally:
                fileobj.close()
                os.unlink(name)

            fd, name = tempfile.mkstemp()
            fileobj = os.fdopen(fd, "w+b")
            try:
                writer = csv.writer(fileobj, dialect=testA, delimiter=';')
                writer.writerow([1, 2, 3])
                fileobj.seek(0)
                self.assertEqual(fileobj.read(), b"1;2;3\r\n")
            finally:
                fileobj.close()
                os.unlink(name)

        finally:
            csv.unregister_dialect('testC')

    def test_bad_dialect(self):
        # Unknown parameter
        self.assertRaises(TypeError, csv.reader, [], bad_attr=0)
        # Bad values
        self.assertRaises(TypeError, csv.reader, [], delimiter=None)
        self.assertRaises(TypeError, csv.reader, [], quoting=-1)
        self.assertRaises(TypeError, csv.reader, [], quoting=100)


class TestCsvBase(unittest.TestCase):
    def readerAssertEqual(self, input, expected_result):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(input)
            fileobj.seek(0)
            reader = csv.reader(fileobj, dialect=self.dialect)
            fields = list(reader)
            self.assertEqual(fields, expected_result)
        finally:
            fileobj.close()
            os.unlink(name)

    def writerAssertEqual(self, input, expected_result):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, dialect=self.dialect)
            writer.writerows(input)
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), expected_result)
        finally:
            fileobj.close()
            os.unlink(name)


class TestDialectExcel(TestCsvBase):
    dialect = 'excel'

    def test_single(self):
        self.readerAssertEqual(b'abc', [['abc']])

    def test_simple(self):
        self.readerAssertEqual(b'1,2,3,4,5', [['1', '2', '3', '4', '5']])

    def test_blankline(self):
        self.readerAssertEqual(b'', [])

    def test_empty_fields(self):
        self.readerAssertEqual(b',', [['', '']])

    def test_singlequoted(self):
        self.readerAssertEqual(b'""', [['']])

    def test_singlequoted_left_empty(self):
        self.readerAssertEqual(b'"",', [['', '']])

    def test_singlequoted_right_empty(self):
        self.readerAssertEqual(b',""', [['', '']])

    def test_single_quoted_quote(self):
        self.readerAssertEqual(b'""""', [['"']])

    def test_quoted_quotes(self):
        self.readerAssertEqual(b'""""""', [['""']])

    def test_inline_quote(self):
        self.readerAssertEqual(b'a""b', [['a""b']])

    def test_inline_quotes(self):
        self.readerAssertEqual(b'a"b"c', [['a"b"c']])

    def test_quotes_and_more(self):
        # Excel would never write a field containing '"a"b', but when
        # reading one, it will return 'ab'.
        self.readerAssertEqual(b'"a"b', [['ab']])

    def test_lone_quote(self):
        self.readerAssertEqual(b'a"b', [['a"b']])

    def test_quote_and_quote(self):
        # Excel would never write a field containing '"a" "b"', but when
        # reading one, it will return 'a "b"'.
        self.readerAssertEqual(b'"a" "b"', [['a "b"']])

    def test_space_and_quote(self):
        self.readerAssertEqual(b' "a"', [[' "a"']])

    def test_quoted(self):
        self.readerAssertEqual(b'1,2,3,"I think, therefore I am",5,6',
                               [['1', '2', '3',
                                 'I think, therefore I am',
                                 '5', '6']])

    def test_quoted_quote(self):
        value = b'1,2,3,"""I see,"" said the blind man","as he picked up his hammer and saw"'
        self.readerAssertEqual(value,
                               [['1', '2', '3',
                                 '"I see," said the blind man',
                                 'as he picked up his hammer and saw']])

    def test_quoted_nl(self):
        input = b'''\
1,2,3,"""I see,""
said the blind man","as he picked up his
hammer and saw"
9,8,7,6'''
        self.readerAssertEqual(input,
                               [['1', '2', '3',
                                   '"I see,"\nsaid the blind man',
                                   'as he picked up his\nhammer and saw'],
                                ['9', '8', '7', '6']])

    def test_dubious_quote(self):
        self.readerAssertEqual(b'12,12,1",', [['12', '12', '1"', '']])

    def test_null(self):
        self.writerAssertEqual([], b'')

    def test_single_writer(self):
        self.writerAssertEqual([['abc']], b'abc\r\n')

    def test_simple_writer(self):
        self.writerAssertEqual([[1, 2, 'abc', 3, 4]],
                               b'1,2,abc,3,4\r\n')

    def test_quotes(self):
        self.writerAssertEqual([[1, 2, 'a"bc"', 3, 4]],
                               b'1,2,"a""bc""",3,4\r\n')

    def test_quote_fieldsep(self):
        self.writerAssertEqual([['abc,def']],
                               b'"abc,def"\r\n')

    def test_newlines(self):
        self.writerAssertEqual([[1, 2, 'a\nbc', 3, 4]],
                               b'1,2,"a\nbc",3,4\r\n')


class EscapedExcel(csv.excel):
    quoting = csv.QUOTE_NONE
    escapechar = '\\'


class TestEscapedExcel(TestCsvBase):
    dialect = EscapedExcel()

    def test_escape_fieldsep(self):
        self.writerAssertEqual([['abc,def']], b'abc\\,def\r\n')

    def test_read_escape_fieldsep(self):
        self.readerAssertEqual(b'abc\\,def\r\n', [['abc,def']])


class QuotedEscapedExcel(csv.excel):
    quoting = csv.QUOTE_NONNUMERIC
    escapechar = '\\'


class TestQuotedEscapedExcel(TestCsvBase):
    dialect = QuotedEscapedExcel()

    def test_write_escape_fieldsep(self):
        self.writerAssertEqual([['abc,def']], b'"abc,def"\r\n')

    def test_read_escape_fieldsep(self):
        self.readerAssertEqual(b'"abc\\,def"\r\n', [['abc,def']])


class TestDictFields(unittest.TestCase):
    # "long" means the row is longer than the number of fieldnames
    # "short" means there are fewer elements in the row than fieldnames
    def test_write_simple_dict(self):
        fd, name = tempfile.mkstemp()
        fileobj = open(name, 'w+b')
        try:
            writer = csv.DictWriter(fileobj, fieldnames=["f1", "f2", "f3"])
            writer.writeheader()
            fileobj.seek(0)
            self.assertEqual(fileobj.readline(), b"f1,f2,f3\r\n")
            writer.writerow({"f1": 10, "f3": "abc"})
            fileobj.seek(0)
            fileobj.readline()  # header
            self.assertEqual(fileobj.read(), b"10,,abc\r\n")
        finally:
            fileobj.close()
            os.unlink(name)

    def test_write_unicode_header_dict(self):
        fd, name = tempfile.mkstemp()
        fileobj = open(name, 'w+b')
        try:
            writer = csv.DictWriter(fileobj, fieldnames=[u"ñ", u"ö"])
            writer.writeheader()
            fileobj.seek(0)
            self.assertEqual(fileobj.readline().decode('utf-8'), u"ñ,ö\r\n")
        finally:
            fileobj.close()
            os.unlink(name)

    def test_write_no_fields(self):
        fileobj = BytesIO()
        self.assertRaises(TypeError, csv.DictWriter, fileobj)

    def test_read_dict_fields(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"1,2,abc\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj,
                                    fieldnames=["f1", "f2", "f3"])
            self.assertEqual(next(reader),
                             {"f1": '1', "f2": '2', "f3": 'abc'})
        finally:
            fileobj.close()
            os.unlink(name)

    def test_read_dict_no_fieldnames(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"f1,f2,f3\r\n1,2,abc\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj)
            self.assertEqual(reader.fieldnames,
                             ["f1", "f2", "f3"])
            self.assertEqual(next(reader),
                             {"f1": '1', "f2": '2', "f3": 'abc'})
        finally:
            fileobj.close()
            os.unlink(name)

    # Two test cases to make sure existing ways of implicitly setting
    # fieldnames continue to work.  Both arise from discussion in issue3436.
    def test_read_dict_fieldnames_from_file(self):
        fd, name = tempfile.mkstemp()
        f = os.fdopen(fd, "w+b")
        try:
            f.write(b"f1,f2,f3\r\n1,2,abc\r\n")
            f.seek(0)
            reader = csv.DictReader(f, fieldnames=next(csv.reader(f)))
            self.assertEqual(reader.fieldnames,
                             ["f1", "f2", "f3"])
            self.assertEqual(next(reader),
                             {"f1": '1', "f2": '2', "f3": 'abc'})
        finally:
            f.close()
            os.unlink(name)

    def test_read_dict_fieldnames_chain(self):
        import itertools
        fd, name = tempfile.mkstemp()
        f = os.fdopen(fd, "w+b")
        try:
            f.write(b"f1,f2,f3\r\n1,2,abc\r\n")
            f.seek(0)
            reader = csv.DictReader(f)
            first = next(reader)
            for row in itertools.chain([first], reader):
                self.assertEqual(reader.fieldnames, ["f1", "f2", "f3"])
                self.assertEqual(row, {"f1": '1', "f2": '2', "f3": 'abc'})
        finally:
            f.close()
            os.unlink(name)

    def test_read_long(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"1,2,abc,4,5,6\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj,
                                    fieldnames=["f1", "f2"])
            self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                             None: ["abc", "4", "5", "6"]})
        finally:
            fileobj.close()
            os.unlink(name)

    def test_read_long_with_rest(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"1,2,abc,4,5,6\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj,
                                    fieldnames=["f1", "f2"], restkey="_rest")
            self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                             "_rest": ["abc", "4", "5", "6"]})
        finally:
            fileobj.close()
            os.unlink(name)

    def test_read_long_with_rest_no_fieldnames(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"f1,f2\r\n1,2,abc,4,5,6\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj, restkey="_rest")
            self.assertEqual(reader.fieldnames, ["f1", "f2"])
            self.assertEqual(next(reader), {"f1": '1', "f2": '2',
                                             "_rest": ["abc", "4", "5", "6"]})
        finally:
            fileobj.close()
            os.unlink(name)

    def test_read_short(self):
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            fileobj.write(b"1,2,abc,4,5,6\r\n1,2,abc\r\n")
            fileobj.seek(0)
            reader = csv.DictReader(fileobj,
                                    fieldnames="1 2 3 4 5 6".split(),
                                    restval="DEFAULT")
            self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                             "4": '4', "5": '5', "6": '6'})
            self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                             "4": 'DEFAULT', "5": 'DEFAULT',
                                             "6": 'DEFAULT'})
        finally:
            fileobj.close()
            os.unlink(name)

    def test_read_multi(self):
        sample = [
            b'2147483648,43.0e12,17,abc,def\r\n',
            b'147483648,43.0e2,17,abc,def\r\n',
            b'47483648,43.0,170,abc,def\r\n'
            ]

        reader = csv.DictReader(sample,
                                fieldnames="i1 float i2 s1 s2".split())
        self.assertEqual(next(reader), {"i1": '2147483648',
                                         "float": '43.0e12',
                                         "i2": '17',
                                         "s1": 'abc',
                                         "s2": 'def'})

    def test_read_with_blanks(self):
        reader = csv.DictReader([b"1,2,abc,4,5,6\r\n", b"\r\n",
                                 b"1,2,abc,4,5,6\r\n"],
                                fieldnames="1 2 3 4 5 6".split())
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})

    def test_read_semi_sep(self):
        reader = csv.DictReader([b"1;2;abc;4;5;6\r\n"],
                                fieldnames="1 2 3 4 5 6".split(),
                                delimiter=';')
        self.assertEqual(next(reader), {"1": '1', "2": '2', "3": 'abc',
                                         "4": '4', "5": '5', "6": '6'})

    def test_empty_file(self):
        csv.DictReader(BytesIO())

class TestArrayWrites(unittest.TestCase):
    def test_int_write(self):
        contents = [(20-i) for i in range(20)]
        a = array.array('i', contents)

        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, dialect="excel")
            writer.writerow(a)
            expected = b",".join([str(i).encode('utf-8') for i in a])+b"\r\n"
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), expected)
        finally:
            fileobj.close()
            os.unlink(name)

    def test_double_write(self):
        contents = [(20-i)*0.1 for i in range(20)]
        a = array.array('d', contents)
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, dialect="excel")
            writer.writerow(a)
            float_repr = str
            if sys.version_info >= (2, 7, 3):
                float_repr = repr
            expected = b",".join([float_repr(i).encode('utf-8') for i in a])+b"\r\n"
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), expected)
        finally:
            fileobj.close()
            os.unlink(name)

    def test_float_write(self):
        contents = [(20-i)*0.1 for i in range(20)]
        a = array.array('f', contents)
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, dialect="excel")
            writer.writerow(a)
            float_repr = str
            if sys.version_info >= (2, 7, 3):
                float_repr = repr
            expected = b",".join([float_repr(i).encode('utf-8') for i in a])+b"\r\n"
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), expected)
        finally:
            fileobj.close()
            os.unlink(name)

    def test_char_write(self):
        a = string.ascii_letters
        fd, name = tempfile.mkstemp()
        fileobj = os.fdopen(fd, "w+b")
        try:
            writer = csv.writer(fileobj, dialect="excel")
            writer.writerow(a)
            expected = ",".join(a).encode('utf-8')+b"\r\n"
            fileobj.seek(0)
            self.assertEqual(fileobj.read(), expected)
        finally:
            fileobj.close()
            os.unlink(name)


class TestUnicode(unittest.TestCase):
    def test_unicode_read(self):
        f = EncodedFile(BytesIO((u"Martin von Löwis,"
                                 u"Marc André Lemburg,"
                                 u"Guido van Rossum,"
                                 u"François Pinard\r\n").encode('iso-8859-1')),
                        data_encoding='iso-8859-1')
        reader = csv.reader(f, encoding='iso-8859-1')
        self.assertEqual(list(reader), [[u"Martin von Löwis",
                                         u"Marc André Lemburg",
                                         u"Guido van Rossum",
                                         u"François Pinard"]])


class TestUnicodeErrors(unittest.TestCase):
    def test_encode_error(self):
        fd = BytesIO()
        writer = csv.writer(fd, encoding='cp1252', errors='xmlcharrefreplace')
        writer.writerow(['hello', chr(2603)])
        self.assertEqual(fd.getvalue(), b'hello,&#2603;\r\n')

    def test_encode_error_dictwriter(self):
        fd = BytesIO()
        dw = csv.DictWriter(fd, ['col1'],
                            encoding='cp1252', errors='xmlcharrefreplace')
        dw.writerow({'col1': chr(2604)})
        self.assertEqual(fd.getvalue(), b'&#2604;\r\n')

    def test_decode_error(self):
        """Make sure the specified error-handling mode is obeyed on readers."""
        file = EncodedFile(BytesIO(u'Löwis,2,3'.encode('iso-8859-1')),
                           data_encoding='iso-8859-1')
        reader = csv.reader(file, encoding='ascii', errors='ignore')
        self.assertEqual(list(reader)[0][0], 'Lwis')

    def test_decode_error_dictreader(self):
        """Make sure the error-handling mode is obeyed on DictReaders."""
        file = EncodedFile(BytesIO(u'name,height,weight\nLöwis,2,3'.encode('iso-8859-1')),
                           data_encoding='iso-8859-1')
        reader = csv.DictReader(file, encoding='ascii', errors='ignore')
        self.assertEqual(list(reader)[0]['name'], 'Lwis')
