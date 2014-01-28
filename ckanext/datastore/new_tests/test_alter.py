import unittest

import nose
import pylons
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.tests as tests
import ckan.new_tests.helpers as helpers
import ckanext.datastore.new_tests.helpers as dsh
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

    @classmethod
    def teardown_class(cls):
        cls.Session.close_all()
        dshelpers.rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def tearDown(self):
        helpers.reset_db()

    def test_alter_name(self):
        resource_id = dsh.create_test_datastore_resource(
            field_name='col1',
            field_type='text',
            record='hello',
        )

        results = helpers.call_action(
            'datastore_rename_column',
            resource_id=resource_id,
            fields=[
                {'from': 'col1', 'to': 'renamed_col1'},
            ],
        )
        fields = dict((i['id'], i['type']) for i in results['fields'])
        self.assertEquals('renamed_col1' in fields, True)

        dsh.delete_test_datastore_resource(resource_id)

    def test_column_does_not_exist(self):
        resource_id = dsh.create_test_datastore_resource(
            field_name='col1',
            field_type='text',
            record='hello',
        )

        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_rename_column',
            resource_id=resource_id,
            fields=[
                {'from': 'doesnotexist', 'to': 'col'},
            ],
        )
        dsh.delete_test_datastore_resource(resource_id)

    def test_bad_name_for_to_column(self):
        resource_id = dsh.create_test_datastore_resource(
            field_name='col1',
            field_type='text',
            record='hello',
        )
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_rename_column',
            resource_id=resource_id,
            fields=[
                {'from': 'col1', 'to': 'col";'},
            ],
        )
        dsh.delete_test_datastore_resource(resource_id)


class TestAlterColumn(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        cls.Session.close_all()
        p.unload('datastore')

    def tearDown(self):
        helpers.reset_db()

    def test_from_text_to_timestamp(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='text_to_timestamp',
            field_type='text',
            record='2010-01-02'
        )

        # run test
        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {
                    'id': 'text_to_timestamp',
                    'from': 'text',
                    'to': 'timestamp',
                    'format': 'yyyymmdd',
                }
            ],
        )

        #check type of our converted field
        fields = dict((i['id'], i['type']) for i in results)
        self.assertEquals(fields['text_to_timestamp'], 'timestamp')

        #now check the value we've converted it to is correct
        data = helpers.call_action(
            'datastore_search_sql',
            sql='select * from "{0}"'.format(resource_id),
        )
        value = data['records'][0]['text_to_timestamp']
        self.assertEquals(value, '2010-01-02T00:00:00')

        #clean up, I'd prefer this in tearDown to guarantee it runs even if
        #there is an exception
        dsh.delete_test_datastore_resource(resource_id)

    def test_from_numeric_to_timestamp(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='numeric_to_timestamp',
            field_type='numeric',
            record=20100102
        )

        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {
                    'id': 'numeric_to_timestamp',
                    'from': 'numeric',
                    'to': 'timestamp',
                    'format': 'yyyymmdd',
                }
            ],
        )
        fields = dict((i['id'], i['type']) for i in results)
        self.assertEquals(fields['numeric_to_timestamp'], 'timestamp')

        #now check the value we've converted it to is correct
        data = helpers.call_action(
            'datastore_search_sql',
            sql='select * from "{0}"'.format(resource_id),
        )
        value = data['records'][0]['numeric_to_timestamp']
        self.assertEquals(value, '2010-01-02T00:00:00')

        #clean up
        dsh.delete_test_datastore_resource(resource_id)

    def test_from_text_to_numeric(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='text_to_numeric',
            field_type='text',
            record='1000'
        )

        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {'id': 'text_to_numeric', 'from': 'text', 'to': 'numeric'},
            ],
        )
        #check type of our converted field
        fields = dict((i['id'], i['type']) for i in results)
        self.assertEquals(fields['text_to_numeric'], 'numeric')

        #now check the value we've converted it to is correct
        data = helpers.call_action(
            'datastore_search_sql',
            sql='select * from "{0}"'.format(resource_id),
        )
        value = data['records'][0]['text_to_numeric']
        self.assertEquals(value, '1000')

        dsh.delete_test_datastore_resource(resource_id)

    def test_from_numeric_to_text(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='numeric_to_text',
            field_type='numeric',
            record=100
        )

        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {'id': 'numeric_to_text', 'from': 'numeric', 'to': 'text'},
            ],
        )

        #check type of our converted field
        fields = dict((i['id'], i['type']) for i in results)
        self.assertEquals(fields['numeric_to_text'], 'text')

        #now check the value we've converted it to is correct
        data = helpers.call_action(
            'datastore_search_sql',
            sql='select * from "{0}"'.format(resource_id),
        )
        value = data['records'][0]['numeric_to_text']
        self.assertEquals(value, '100')

        dsh.delete_test_datastore_resource(resource_id)

    def test_from_timestamp_to_text(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='timestamp_to_text',
            field_type='timestamp',
            record='2010-01-02',
        )

        results = helpers.call_action(
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {
                    'id': 'timestamp_to_text',
                    'from': 'timestamp',
                    'to': 'text',
                    'format': 'YYYYMMDD',
                }
            ],
        )
        fields = dict((i['id'], i['type']) for i in results)
        self.assertEquals(fields['timestamp_to_text'], 'text')

        #now check the value we've converted it to is correct
        data = helpers.call_action(
            'datastore_search_sql',
            sql='select * from "{0}"'.format(resource_id),
        )
        value = data['records'][0]['timestamp_to_text']
        self.assertEquals(value, '2010-01-02 00:00:00')

        dsh.delete_test_datastore_resource(resource_id)

    def test_empty_fields(self):
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id='',
            fields=[],
        )

    def test_column_does_not_exist(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='exists',
            field_type='timestamp',
            record='2010-01-02',
        )

        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id=resource_id,
            fields=[
                {'id': 'doesnotexist', 'from': 'text', 'to': 'numeric'},
            ],
        )

        dsh.delete_test_datastore_resource(resource_id)

    def test_column_type_does_not_exist(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='text',
            field_type='numeric',
            record=100,
        )
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id='',
            fields=[
                {'id': 'text', 'from': 'numeric', 'to': 'does notexist'},
            ],
        )
        dsh.delete_test_datastore_resource(resource_id)

    def test_date_conversion_bad_format(self):
        # create test datastore table
        resource_id = dsh.create_test_datastore_resource(
            field_name='col',
            field_type='text',
            record='2000-01-01',
        )
        self.assertRaises(
            toolkit.ValidationError,
            helpers.call_action,
            'datastore_alter_column_type',
            resource_id='',
            fields=[
                {
                    'id': 'col',
                    'from': 'text',
                    'to': 'timestamp',
                    'format': "';"
                }
            ],
        )
        dsh.delete_test_datastore_resource(resource_id)
