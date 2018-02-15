# encoding: utf-8

import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckan.model.metadata import CkanMigrationMetaData
from ckan.common import config


assert_equals = nose.tools.assert_equals


class TestMetaData(object):

    def test_set_schema(self):

        config[u'ckan.migrations.target_schema'] = u'test_schema'

        metadata = CkanMigrationMetaData()

        assert_equals(metadata.schema, u'test_schema')
