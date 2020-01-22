# encoding: utf-8

import pytest

import ckan.plugins.toolkit as tk


@pytest.mark.parametrize(
    "version,bound,value,expected",
    [
        ("2", "min", "1", True),
        ("2", "min", "2", True),
        ("2", "min", "3", False),
        ("2.1", "min", "1", True),
        ("2.1", "min", "3", False),
        ("2.1", "min", "1.1", True),
        ("2.1", "min", "2.1", True),
        ("2.1", "min", "3.1", False),
        ("1.5", "min", "1.4", True),
        ("1.5", "min", "1.6", False),
        ("2.2", "min", "1.2.3", True),
        ("2.2", "min", "3.2.1", False),
        ("2.2", "min", "2.1.3", True),
        ("2.2", "min", "2.3.0", False),
        ("2.2", "min", "2.1.3", True),
        ("2", "min", "1", True),
        ("2.2", "min", "2.2.1", False),
        ("1.5.1", "min", "0.6", True),
        ("1.5.1", "min", "2.4", False),
        ("1.5.1", "min", "1.5", True),
        ("1.5.1", "min", "1.6", False),
        ("1.5.1", "min", "0.5.1", True),
        ("1.5.1", "min", "1.5.1", True),
        ("1.5.1", "min", "1.5.2", False),
        ("1.5.1", "min", "1.4.1", True),
        ("1.5.1", "min", "1.6.1", False),
        ("1.5.1", "min", "1.5.0", True),
        ("1.5.1", "min", "1.5.2", False),
        ("2", "max", "1", False),
        ("2", "max", "2", True),
        ("2", "max", "3", True),
        ("2.1", "max", "1", False),
        ("2.1", "max", "3", True),
        ("2.1", "max", "1.1", False),
        ("2.1", "max", "2.1", True),
        ("2.1", "max", "3.1", True),
        ("1.5", "max", "1.4", False),
        ("1.5", "max", "1.6", True),
        ("2.2", "max", "1.2.3", False),
        ("2.2", "max", "3.2.1", True),
        ("2.2", "max", "2.1.3", False),
        ("2.2", "max", "2.3.0", True),
        ("2.2", "max", "2.1.3", False),
        ("2.2", "max", "2.2.1", True),
        ("1.5.1", "max", "0.6", False),
        ("1.5.1", "max", "2.4", True),
        ("1.5.1", "max", "1.5", False),
        ("1.5.1", "max", "1.6", True),
        ("1.5.1", "max", "0.5.1", False),
        ("1.5.1", "max", "1.5.1", True),
        ("1.5.1", "max", "1.5.2", True),
        ("1.5.1", "max", "1.4.1", False),
        ("1.5.1", "max", "1.6.1", True),
        ("1.5.1", "max", "1.5.0", False),
        ("1.5.1", "max", "1.5.2", True),
    ],
)
def test_check_ckan_version(version, bound, value, expected, monkeypatch):
    # test name numbers refer to:
    #   * number of numbers in the ckan version
    #   * number of numbers in the checked version
    #   * the index of the number being tested in the checked version

    monkeypatch.setattr(tk.ckan, u"__version__", version)
    kwargs = {bound + u"_version": value}
    assert tk.check_ckan_version(**kwargs) is expected


def test_no_raise(monkeypatch):
    monkeypatch.setattr(tk.ckan, u"__version__", u"2")
    tk.requires_ckan_version(min_version=u"2")


def test_raise(monkeypatch):
    monkeypatch.setattr(tk.ckan, u"__version__", u"2")
    with pytest.raises(tk.CkanVersionException):
        tk.requires_ckan_version(min_version=u"3")


def test_call_helper():
    # the null_function would return ''
    assert tk.h.icon_url(u"x")


def test_tk_helper_attribute_error_on_missing_helper():
    with pytest.raises(AttributeError):
        getattr(tk.h, u"not_a_real_helper_function")


def test_tk_helper_as_attribute_missing_helper():
    """Directly attempt access to module function"""
    with pytest.raises(AttributeError):
        tk.h.nothere()


def test_tk_helper_as_item_missing_helper():
    """Directly attempt access as item"""
    with pytest.raises(tk.HelperError):
        tk.h[u"nothere"]()
