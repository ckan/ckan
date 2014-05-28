import ckanext.datastore.helpers as helpers


class TestTypeGetters(object):
    def test_get_list(self):
        assert helpers.get_list(None) is None
        assert helpers.get_list([]) == []
        assert helpers.get_list('') == []
        assert helpers.get_list('foo') == ['foo']
        assert helpers.get_list('foo, bar') == ['foo', 'bar']
        assert helpers.get_list('foo_"bar, baz') == ['foo_"bar', 'baz']
        assert helpers.get_list('"foo", "bar"') == ['foo', 'bar']
        assert helpers.get_list(u'foo, bar') == ['foo', 'bar']
        assert helpers.get_list(['foo', 'bar']) == ['foo', 'bar']
        assert helpers.get_list([u'foo', u'bar']) == ['foo', 'bar']
        assert helpers.get_list(['foo', ['bar', 'baz']]) == ['foo', ['bar', 'baz']]
