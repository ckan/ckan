"""Tests for helpers.py."""

import ckanext.logs.helpers as helpers


def test_logs_hello():
    assert helpers.logs_hello() == "Hello, logs!"
