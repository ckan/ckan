import unittest

from formencode.variabledecode import variable_decode, variable_encode


class TestVariableDecode(unittest.TestCase):

    def test_list_decode(self):
        src = {'a-0': 'a', 'a-1': 'b', 'a-2': 'c'}
        expect = {'a': ['a', 'b', 'c']}

        self.assertEqual(expect, variable_decode(src))

    def test_list_decode_non_int(self):
        src = {'a-0': 'a', 'a-a': 'b', 'a-2': 'c'}
        expect = {'a': ['a', 'c'], 'a-a': 'b'}

        self.assertEqual(expect, variable_decode(src))

    def test_list_decode_double_dash(self):
        src = {'a-0': 'a', 'a-1-2': 'b', 'a-3': 'c'}
        expect = {'a': ['a', 'c'], 'a-1-2': 'b'}

        self.assertEqual(expect, variable_decode(src))

    def test_list_decode_non_int_nested(self):
        src = {'a-0.name': 'a', 'a-a.name': 'b', 'a-2.name': 'c'}
        expect = {'a': [{'name': 'a'}, {'name': 'c'}], 'a-a': {'name': 'b'}}

        self.assertEqual(expect, variable_decode(src))

    def test_dict_decode(self):
        src = {'a.a': 'a', 'a.b': 'b', 'a.c': 'c'}
        expect = {'a': {'a': 'a', 'b': 'b', 'c': 'c'}}

        self.assertEqual(expect, variable_decode(src))

    def test_list_dict(self):
        src = {'a-0.name': 'a', 'a-1.name': 'b', 'a-2.name': 'c'}
        expect = {'a': [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}]}

        self.assertEqual(expect, variable_decode(src))

    def test_dict_list_dict(self):
        src = {'a.b-0.name': 'a', 'a.b-1.name': 'b', 'a.b-2.name': 'c'}
        expect = {'a': {'b': [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}]}}

        self.assertEqual(expect, variable_decode(src))


class TestVariableEncode(unittest.TestCase):

    def test_list_encode(self):
        src = {'a': ['a', 'b', 'c']}
        expect = {'a--repetitions': '3', 'a-0': 'a', 'a-1': 'b', 'a-2': 'c'}

        self.assertEqual(expect, variable_encode(src))

    def test_list_encode_non_int(self):
        src = {'a': ['a', 'c'], 'a-a': 'b'}
        expect = {'a--repetitions': '2', 'a-0': 'a', 'a-a': 'b', 'a-1': 'c'}

        self.assertEqual(expect, variable_encode(src))

    def test_dict_encode(self):
        src = {'a': {'a': 'a', 'b': 'b', 'c': 'c'}}
        expect = {'a.a': 'a', 'a.b': 'b', 'a.c': 'c'}

        self.assertEqual(expect, variable_encode(src))
