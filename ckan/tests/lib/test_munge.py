from nose.tools import assert_equal

import ckan.lib.munge

class TestMunge:
    def test_munge_name(self):
        def test_munge(title, expected_munge):
            munge = ckan.lib.munge.munge_name(title)
            assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('bad spaces', 'bad-spaces')
        test_munge('s', 's_') # too short
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u') 

    def test_munge_title_to_name(self):
        def test_munge(title, expected_munge):
            munge = ckan.lib.munge.munge_title_to_name(title)
            assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('some spaces  here', 'some-spaces-here')
        test_munge('s', 's_') # too short
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u') 
        test_munge('reallylong'*12 , 'reallylong'*9 + 'reall') 
        test_munge('reallylong'*12 + ' - 2012' , 'reallylong'*9 + '-2012') 

    def test_munge_tag(self):
        def test_munge(title, expected_munge):
            munge = ckan.lib.munge.munge_tag(title)
            assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('s', 's_') # too short
        test_munge('some spaces  here', 'some-spaces--here')
        test_munge('random:other%character&', 'randomothercharacter')
