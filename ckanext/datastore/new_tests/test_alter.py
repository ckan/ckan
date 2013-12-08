import unittest

import nose
import pylons
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.model as model
import ckan.tests as tests
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckanext.datastore.tests.helpers as dshelpers
import ckan.plugins.toolkit as toolkit

import ckanext.datastore.db as db


class TestDatastoreRenameColumn(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

        helpers.reset_db()

        # Note: test data for this test is created here and in the
        # teardown_class this means test data persists between tests
        package = factories.Package.create()
        cls.resource = factories.Resource.create(
            package_id=package['id'], url_type='datastore')

        helpers.call_action(
            'datastore_create',
            resource_id=cls.resource['id'],
            fields=[
                {'id': 'col1', 'type': 'text'},
                {'id': 'col2', 'type': 'text'}
            ],
            records=[
                {'col1': 'hello', 'col2': 'hello'},
                {'col1': 'hello', 'col2': 'hello'},
            ],
        )

    @classmethod
    def teardown_class(cls):
        cls.Session.close_all()
        dshelpers.rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_alter_name(self):
        results = helpers.call_action(
            'datastore_rename_column',
            resource_id=TestDatastoreRenameColumn.resource['id'],
            fields=[
                {'from': 'col1', 'to': 'renamed_col1'},
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals('renamed_col1' in fields, True)
        self.assertEquals('col2' in fields, True)

        #rename the column back to it's original name
        helpers.call_action(
            'datastore_rename_column',
            resource_id=TestDatastoreRenameColumn.resource['id'],
            fields=[
                {'from': 'renamed_col1', 'to': 'col1'},
            ],
        )

    def test_column_does_not_exist(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_rename_column',
            resource_id=TestDatastoreRenameColumn.resource['id'],
            fields=[
                {'from': 'doesnotexist', 'to': 'col'},
            ],
        )

    def test_bad_name_for_to_column(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_rename_column',
            resource_id=TestDatastoreRenameColumn.resource['id'],
            fields=[
                {'from': 'col1', 'to': 'col";'},
            ],
        )


class TestDatastoreAlterColumn(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

        helpers.reset_db()

        # Note: test data for this test is created here and in the
        # teardown_class this means test data persists between tests
        package = factories.Package.create()
        cls.resource = factories.Resource.create(
            package_id=package['id'], url_type='datastore')

        helpers.call_action(
            'datastore_create',
            resource_id=cls.resource['id'],
            fields=[
                {'id': 'text_to_numeric', 'type': 'text'},
                {'id': 'numeric_to_text', 'type': 'numeric'},
                {'id': 'text_to_timestamp', 'type': 'text'},
                {'id': 'timestamp_to_text', 'type': 'timestamp'},
                {'id': 'numeric_to_timestamp', 'type': 'numeric'},
                {'id': 'text', 'type': 'text'},
            ],
            records=[
                {
                    'text_to_numeric': '1',
                    'numeric_to_text': 100,
                    'text_to_timestamp': '2010-01-02',
                    'timestamp_to_text': '2010-01-02',
                    'numeric_to_timestamp': 20100102,
                    'text': 'some text',
                    'timestamp': '2010-01-01',
                },
                {
                    'text_to_numeric': '1',
                    'numeric_to_text': None,
                    'text_to_timestamp': None,
                    'timestamp_to_text': None,
                    'numeric_to_timestamp': None,
                },
            ],
        )

    @classmethod
    def teardown_class(cls):
        cls.Session.close_all()
        dshelpers.rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_from_text_to_numeric(self):
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {'id': 'text_to_numeric', 'type': 'numeric'},
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals(fields['text_to_numeric'], 'numeric')
        
    def test_from_numeric_to_text(self):
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {'id': 'numeric_to_text', 'type': 'text'},
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals(fields['numeric_to_text'], 'text')

    def test_from_text_to_timestamp(self):
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[{
                    'id': 'text_to_timestamp',
                    'type': 'timestamp',
                    'format': 'YYYY-MM-DD',
            }],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals(fields['text_to_timestamp'], 'timestamp')

    def test_from_timestamp_to_text(self):
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {
                    'id': 'timestamp_to_text',
                    'type': 'text',
                    'format': 'YYYY-MM-DD',
                }
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals(fields['timestamp_to_text'], 'text')

    def test_from_numeric_to_timestamp(self):
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {
                    'id': 'numeric_to_timestamp',
                    'type': 'timestamp',
                }
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals(fields['numeric_to_timestamp'], 'timestamp')

    def test_empty_fields(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[],
        )

    def test_column_does_not_exist(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {'id': 'doesnotexist', 'type': 'numeric'},
            ],
        )

    def test_column_type_does_not_exist(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {'id': 'text', 'type': 'does notexist'},
            ],
        )

    def test_date_conversion_bad_format(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id=TestDatastoreAlterColumn.resource['id'],
            fields=[
                {'id': 'col3', 'type': 'timestamp', 'format': "';"}
            ],
        )
