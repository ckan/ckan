from nose.tools import assert_equal

from ckan.lib.munge import munge_title_to_name, munge_name

class TestMunge:
    def test_munge_title_to_name(self):
        def test_munge(title, expected_munge):
            munge = munge_title_to_name(title)
            assert_equal(munge, expected_munge)

        test_munge('Adult participation in learning', 'adult-participation-in-learning')
        test_munge('Alcohol Profile: Alcohol-specific hospital admission, males', 'alcohol-profile-alcohol-specific-hospital-admission-males')
        test_munge('Age and limiting long-term illness by NS-SeC', 'age-and-limiting-long-term-illness-by-ns-sec')
        test_munge('Higher Education Statistics: HE qualifications obtained in the UK by level, mode of study, domicile, gender, class of first degree and subject area 2001/02', 'higher-education-statistics-he-qualifications-obtained-in-the-uk-by-level-mode-of-study-2001-02')        

    def test_munge_name(self):
        def test_munge(title, expected_munge):
            munge = munge_name(title)
            assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('bad spaces', 'bad-spaces')
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u')
