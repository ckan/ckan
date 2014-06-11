# -*- coding: utf-8 -*-
'''Unit tests for ckan/logic/converters.py.

'''
import unittest
import ckan.logic.converters as converters


class TestRemoveWhitespaceConverter(unittest.TestCase):
    def test_leading_space(self):
        string = '  http://example.com'
        expected = 'http://example.com'
        converted = converters.remove_whitespace(string, {})
        self.assertEqual(expected, converted)

    def test_trailing_space(self):
        string = 'http://example.com  '
        expected = 'http://example.com'
        converted = converters.remove_whitespace(string, {})
        self.assertEqual(expected, converted)

    def test_space_between(self):
        string = 'http://example.com/space between url '
        expected = 'http://example.com/space between url'
        converted = converters.remove_whitespace(string, {})
        self.assertEqual(expected, converted)

    def test_not_a_string(self):
        string = 12345
        expected = 12345
        converted = converters.remove_whitespace(string, {})
        self.assertEqual(string, converted)
