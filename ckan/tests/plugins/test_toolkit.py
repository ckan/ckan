# encoding: utf-8

from nose.tools import assert_equal, assert_raises, assert_true, raises

from ckan.plugins import toolkit as tk


class TestCheckCkanVersion(object):
    @classmethod
    def setup_class(cls):
        # save the ckan version so it can be restored at the end of the test
        cls.__original_ckan_version = tk.ckan.__version__

    @classmethod
    def teardown_class(cls):
        # restore the correct ckan version
        tk.ckan.__version__ = cls.__original_ckan_version

    # test name numbers refer to:
    #   * number of numbers in the ckan version
    #   * number of numbers in the checked version
    #   * the index of the number being tested in the checked version

    def test_min_111_lt(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(min_version='1'), True)

    def test_min_111_eq(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(min_version='2'), True)

    def test_min_111_gt(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(min_version='3'), False)

    def test_min_211_lt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(min_version='1'), True)

    def test_min_211_gt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(min_version='3'), False)

    def test_min_221_lt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(min_version='1.1'), True)

    def test_min_221_eq(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(min_version='2.1'), True)

    def test_min_221_gt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(min_version='3.1'), False)

    def test_min_222_lt(self):
        tk.ckan.__version__ = '1.5'
        assert_equal(tk.check_ckan_version(min_version='1.4'), True)

    def test_min_222_gt(self):
        tk.ckan.__version__ = '1.5'
        assert_equal(tk.check_ckan_version(min_version='1.6'), False)

    def test_min_231_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='1.2.3'), True)

    def test_min_231_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='3.2.1'), False)

    def test_min_232_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='2.1.3'), True)

    def test_min_232_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='2.3.0'), False)

    def test_min_233_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='2.1.3'), True)

    def test_min_233_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(min_version='2.2.1'), False)

    def test_min_321_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='0.6'), True)

    def test_min_321_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='2.4'), False)

    def test_min_322_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.5'), True)

    def test_min_322_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.6'), False)

    def test_min_331_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='0.5.1'), True)

    def test_min_331_eq(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.5.1'), True)

    def test_min_331_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.5.2'), False)

    def test_min_332_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.4.1'), True)

    def test_min_332_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.6.1'), False)

    def test_min_333_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.5.0'), True)

    def test_min_333_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(min_version='1.5.2'), False)

    def test_max_111_lt(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(max_version='1'), False)

    def test_max_111_eq(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(max_version='2'), True)

    def test_max_111_gt(self):
        tk.ckan.__version__ = '2'
        assert_equal(tk.check_ckan_version(max_version='3'), True)

    def test_max_211_lt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(max_version='1'), False)

    def test_max_211_gt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(max_version='3'), True)

    def test_max_221_lt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(max_version='1.1'), False)

    def test_max_221_eq(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(max_version='2.1'), True)

    def test_max_221_gt(self):
        tk.ckan.__version__ = '2.1'
        assert_equal(tk.check_ckan_version(max_version='3.1'), True)

    def test_max_222_lt(self):
        tk.ckan.__version__ = '1.5'
        assert_equal(tk.check_ckan_version(max_version='1.4'), False)

    def test_max_222_gt(self):
        tk.ckan.__version__ = '1.5'
        assert_equal(tk.check_ckan_version(max_version='1.6'), True)

    def test_max_231_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='1.2.3'), False)

    def test_max_231_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='3.2.1'), True)

    def test_max_232_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='2.1.3'), False)

    def test_max_232_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='2.3.0'), True)

    def test_max_233_lt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='2.1.3'), False)

    def test_max_233_gt(self):
        tk.ckan.__version__ = '2.2'
        assert_equal(tk.check_ckan_version(max_version='2.2.1'), True)

    def test_max_321_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='0.6'), False)

    def test_max_321_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='2.4'), True)

    def test_max_322_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.5'), False)

    def test_max_322_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.6'), True)

    def test_max_331_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='0.5.1'), False)

    def test_max_331_eq(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.5.1'), True)

    def test_max_331_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.5.2'), True)

    def test_max_332_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.4.1'), False)

    def test_max_332_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.6.1'), True)

    def test_max_333_lt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.5.0'), False)

    def test_max_333_gt(self):
        tk.ckan.__version__ = '1.5.1'
        assert_equal(tk.check_ckan_version(max_version='1.5.2'), True)


class TestRequiresCkanVersion(object):
    @classmethod
    def setup_class(cls):
        # save the ckan version so it can be restored at the end of the test
        cls.__original_ckan_version = tk.ckan.__version__

    @classmethod
    def teardown_class(cls):
        # restore the correct ckan version
        tk.ckan.__version__ = cls.__original_ckan_version

    # Assume the min_version and max_version params work ok since they are just
    # passed to check_ckan_version which is tested above.

    def test_no_raise(self):
        tk.ckan.__version__ = '2'
        tk.requires_ckan_version(min_version='2')

    def test_raise(self):
        tk.ckan.__version__ = '2'
        assert_raises(tk.CkanVersionException,
                      tk.requires_ckan_version, min_version='3')


class TestToolkitHelper(object):
    def test_call_helper(self):
        # the null_function would return ''
        assert_true(tk.h.icon_url('x'))

    def test_tk_helper_attribute_error_on_missing_helper(self):
        assert_raises(AttributeError, getattr,
                      tk.h, 'not_a_real_helper_function')

    @raises(AttributeError)
    def test_tk_helper_as_attribute_missing_helper(self):
        '''Directly attempt access to module function'''
        tk.h.nothere()

    @raises(tk.HelperError)
    def test_tk_helper_as_item_missing_helper(self):
        '''Directly attempt access as item'''
        tk.h['nothere']()
