# encoding: utf-8

import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckan.model.metadata import CkanMetaData
from ckan.common import config


assert_equals = nose.tools.assert_equals


class TestMetaData(object):

    def test_set_schema(self):

        config['ckan.migrations.target_schema'] = 'test_schema'

        metadata = CkanMetaData()

        assert_equals(metadata.schema, 'test_schema')
