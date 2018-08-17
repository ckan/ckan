# encoding: utf-8

import copy
from nose.tools import eq_, assert_not_in

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.migration.migrate_package_activity import migrate_dataset
from ckan.model.activity import package_activity_list
from ckan import model


class TestMigrate(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_migration(self):
        # Test that the migration correctly takes the package_revision (etc)
        # tables and populates the Activity.data, i.e. it does it the same as
        # if you made a change to the dataset with the current version of CKAN
        # and the Activity was created by activity_stream_item().
        dataset = factories.Dataset(resources=[
            {u'url': u'http://example.com/a.csv', u'format': u'csv'}
        ])
        activity = package_activity_list(dataset['id'], 0, 0)[0]
        activity_data_as_it_should_be = copy.deepcopy(activity.data)

        # Remove 'activity.data.package' to provoke the migration to regenerate
        # it from package_revision (etc)
        activity = model.Activity.get(activity.id)
        del activity.data['package']
        model.repo.commit_and_remove()
        migrate_dataset(dataset['name'])

        activity_data_migrated = \
            package_activity_list(dataset['id'], 0, 0)[0].data
        eq_(activity_data_as_it_should_be, activity_data_migrated)

    def test_migration_with_multiple_revisions(self):
        dataset = factories.Dataset(resources=[
            {u'url': u'http://example.com/a.csv', u'format': u'csv'}
        ])
        dataset['title'] = u'Title 2'
        helpers.call_action(u'package_update', **dataset)
        dataset['title'] = u'Title 3'
        helpers.call_action(u'package_update', **dataset)

        activity = package_activity_list(dataset['id'], 0, 0)[1]
        activity_data_as_it_should_be = copy.deepcopy(activity.data)

        # Remove 'activity.data.package' to provoke the migration to regenerate
        # it from package_revision (etc)
        activity = model.Activity.get(activity.id)
        del activity.data['package']
        model.repo.commit_and_remove()
        migrate_dataset(dataset['name'])

        activity_data_migrated = \
            package_activity_list(dataset['id'], 0, 0)[1].data
        eq_(activity_data_as_it_should_be, activity_data_migrated)
        eq_(activity_data_migrated['package']['title'], u'Title 2')

    def test_a_contemporary_activity_needs_no_migration(self):
        # An Activity created by a change under the current CKAN should not
        # need a migration - check it does a nop
        dataset = factories.Dataset(resources=[
            {u'url': u'http://example.com/a.csv', u'format': u'csv'}
        ])
        activity = package_activity_list(dataset['id'], 0, 0)[0]
        activity_data_before = copy.deepcopy(activity.data)

        migrate_dataset(dataset['name'])

        activity_data_after = package_activity_list(dataset['id'], 0, 0)[0].data
        eq_(activity_data_before, activity_data_after)
