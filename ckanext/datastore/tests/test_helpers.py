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
