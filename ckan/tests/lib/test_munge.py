from nose.tools import assert_equal

from ckan.lib.munge import munge_name

class TestMunge:
    def test_munge_name(self):
        def test_munge(title, expected_munge):
            munge = munge_name(title)
            assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('bad spaces', 'bad-spaces')
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u') 
