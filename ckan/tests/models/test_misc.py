from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model
from ckan.model.misc import escape_sql_like_special_characters

class TestRevisionExtraAttributes:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_revision_packages(self):
        rev = model.repo.youngest_revision()
        assert len(rev.packages) == 2
        assert rev.packages[0].__class__.__name__ == 'Package'
        names = [ p.name for p in rev.packages ]
        assert 'annakarenina' in names

    def test_revision_user(self):
        rev = model.repo.youngest_revision()
        assert rev.user is not None, rev
        assert rev.user.name == rev.author

_sql_escape = escape_sql_like_special_characters
class TestEscapeSqlLikeCharacters(object):
    """
    Tests for model.misc.escape_sql_like_special_characters
    """

    def test_identity(self):
        """Asserts that it escapes nothing if nothing needs escaping"""
        terms = ['',
                 'word',
                 'two words']
        for term, expected_term in zip(terms, terms):
            assert_equal(_sql_escape(term), expected_term)

    def test_escape_chararacter_is_escaped(self):
        """Asserts that the escape character is escaped"""
        term = r'backslash \ character'
        assert_equal (_sql_escape(term, escape='\\'),
                      r'backslash \\ character')

        term = 'surprise!'
        assert_equal (_sql_escape(term, escape='!'),
                      r'surprise!!')

    def test_default_escape_character_is_a_backslash(self):
        """Asserts that the default escape character is the backslash"""
        term = r'backslash \ character'
        assert_equal (_sql_escape(term),
                      r'backslash \\ character')

    def test_sql_like_special_characters_are_escaped(self):
        """Asserts that '%' and '_' are escaped correctly"""
        terms = [
            (r'percents %', r'percents \%'),
            (r'underscores _', r'underscores \_'),
            (r'backslash \ ', r'backslash \\ '),
            (r'all three \ _%', r'all three \\ \_\%'),
            ]

        for term, expected_result in terms:
            assert_equal(_sql_escape(term), expected_result)

