from nose import tools as nose_tools

from ckan.lib.munge import (munge_filename, munge_name,
                            munge_title_to_name, munge_tag)


class TestMungeFilename(object):

    def test_munge_filename_with_hyphens_multiple_pass(self):
        '''
        Munging a filename with spaces multiple times produces same result.
        '''
        filename = '2014-11-10 12:24:05.340603my_image.jpeg'
        expected_filename = '20141110-122405.340603myimage.jpeg'

        # Munge once
        first_munged_filename = munge_filename(filename)
        nose_tools.assert_equal(expected_filename, first_munged_filename)
        # Munge twice
        second_munged_filename = munge_filename(first_munged_filename)
        nose_tools.assert_equal(expected_filename, second_munged_filename)


class TestMungeName(object):

    def test_munge_name(self):
        def test_munge(title, expected_munge):
            munge = munge_name(title)
            nose_tools.assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('bad spaces', 'bad-spaces')
        test_munge('s', 's_')  # too short
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u')


class TestMungeTitleToName(object):

    def test_munge_title_to_name(self):
        def test_munge(title, expected_munge):
            munge = munge_title_to_name(title)
            nose_tools.assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('some spaces  here', 'some-spaces-here')
        test_munge('s', 's_')  # too short
        test_munge('random:other%character&', 'random-othercharacter')
        test_munge(u'u with umlaut \xfc', 'u-with-umlaut-u')
        test_munge('reallylong' * 12, 'reallylong' * 9 + 'reall')
        test_munge('reallylong' * 12 + ' - 2012', 'reallylong' * 9 + '-2012')


class TestMungeTag:

    def test_munge_tag(self):
        def test_munge(title, expected_munge):
            munge = munge_tag(title)
            nose_tools.assert_equal(munge, expected_munge)

        test_munge('unchanged', 'unchanged')
        test_munge('s', 's_')  # too short
        test_munge('some spaces  here', 'some-spaces--here')
        test_munge('random:other%character&', 'randomothercharacter')
