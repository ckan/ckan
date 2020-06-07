# encoding: utf-8

import pytest
from ckan.tests.legacy import CreateTestData
import ckan.model as model
from ckan.model.misc import escape_sql_like_special_characters

_sql_escape = escape_sql_like_special_characters


class TestEscapeSqlLikeCharacters(object):
    """
    Tests for model.misc.escape_sql_like_special_characters
    """

    def test_identity(self):
        """Asserts that it escapes nothing if nothing needs escaping"""
        terms = ["", "word", "two words"]
        for term, expected_term in zip(terms, terms):
            assert _sql_escape(term) == expected_term

    def test_escape_chararacter_is_escaped(self):
        """Asserts that the escape character is escaped"""
        term = r"backslash \ character"
        assert _sql_escape(term, escape="\\") == r"backslash \\ character"

        term = "surprise!"
        assert _sql_escape(term, escape="!") == r"surprise!!"

    def test_default_escape_character_is_a_backslash(self):
        """Asserts that the default escape character is the backslash"""
        term = r"backslash \ character"
        assert _sql_escape(term) == r"backslash \\ character"

    def test_sql_like_special_characters_are_escaped(self):
        """Asserts that '%' and '_' are escaped correctly"""
        terms = [
            (r"percents %", r"percents \%"),
            (r"underscores _", r"underscores \_"),
            (r"backslash \ ", r"backslash \\ "),
            (r"all three \ _%", r"all three \\ \_\%"),
        ]

        for term, expected_result in terms:
            assert _sql_escape(term) == expected_result
