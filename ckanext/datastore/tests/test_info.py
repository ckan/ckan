# encoding: utf-8

import json
import nose
import pprint

import pylons
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
from ckan.tests.legacy import is_datastore_supported

import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import extract, rebuild_all_dbs

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestDatastoreInfo(object):
    @classmethod
    def setup_class(cls):
        if not is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        plugin = p.load('datastore')
        if plugin.legacy_mode:
            # make sure we undo adding the plugin
            p.unload('datastore')
            raise nose.SkipTest("Info is not supported in legacy mode")

    @classmethod
    def teardown_class(cls):
        p.unload('datastore')
        helpers.reset_db()

    def test_info_success(self):
        resource = factories.Resource()
        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': [
                {'from': 'Brazil', 'to': 'Brazil', 'num': 2},
                {'from': 'Brazil', 'to': 'Italy', 'num': 22}
            ],
        }
        result = helpers.call_action('datastore_create', **data)

        info = helpers.call_action('datastore_info', id=resource['id'])

        assert info['meta']['count'] == 2, info['meta']
        assert len(info['schema']) == 3
        assert info['schema']['to'] == 'text'
        assert info['schema']['from'] == 'text'
        assert info['schema']['num'] == 'number', info['schema']
