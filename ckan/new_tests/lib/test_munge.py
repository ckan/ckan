from nose import tools as nose_tools

from ckan.lib.munge import munge_filename


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
