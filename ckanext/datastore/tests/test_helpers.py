import ckanext.datastore.helpers as helpers


class TestTypeGetters(object):
    def test_get_list(self):
        get_list = helpers.get_list
        assert get_list(None) is None
        assert get_list([]) == []
        assert get_list('') == []
        assert get_list('foo') == ['foo']
        assert get_list('foo, bar') == ['foo', 'bar']
        assert get_list('foo_"bar, baz') == ['foo_"bar', 'baz']
        assert get_list('"foo", "bar"') == ['foo', 'bar']
        assert get_list(u'foo, bar') == ['foo', 'bar']
        assert get_list(['foo', 'bar']) == ['foo', 'bar']
        assert get_list([u'foo', u'bar']) == ['foo', 'bar']
        assert get_list(['foo', ['bar', 'baz']]) == ['foo', ['bar', 'baz']]

    def test_is_single_statement(self):
        singles = ['SELECT * FROM footable',
                   'SELECT * FROM "bartable"',
                   'SELECT * FROM "bartable";',
                   'SELECT * FROM "bart;able";',
                   "select 'foo'||chr(59)||'bar'"]

        multiples = ['SELECT * FROM abc; SET LOCAL statement_timeout to'
                     'SET LOCAL statement_timeout to; SELECT * FROM abc',
                     'SELECT * FROM "foo"; SELECT * FROM "abc"']

        for single in singles:
            assert helpers.is_single_statement(single) is True

        for multiple in multiples:
            assert helpers.is_single_statement(multiple) is False
