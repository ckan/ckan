"""Tests for helpers.py."""

import ckanext.statistical_org.helpers as helpers


def test_statistical_org_hello():
    assert helpers.statistical_org_hello() == "Hello, statistical_org!"
