#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mock

import six

from migrate.changeset.databases import ibmdb2
from migrate.tests import fixture


class TestIBMDBDialect(fixture.Base):
    """
    Test class for ibmdb2 dialect unit tests which do not require
    a live backend database connection.
    """

    def test_is_unique_constraint_with_null_cols_supported(self):
        test_values = {
            '10.1': False,
            '10.4.99': False,
            '10.5': True,
            '10.5.1': True
        }
        for version, supported in six.iteritems(test_values):
            mock_dialect = mock.MagicMock()
            mock_dialect.dbms_ver = version
            self.assertEqual(
                supported,
                ibmdb2.is_unique_constraint_with_null_columns_supported(
                    mock_dialect),
                'Assertion failed on version: %s' % version)
