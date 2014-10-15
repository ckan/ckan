import pylons
import sqlalchemy.orm as orm
import nose

import ckanext.datastore.helpers as datastore_helpers
import ckanext.datastore.tests.helpers as datastore_test_helpers
import ckanext.datastore.db as db


eq_ = nose.tools.eq_


class TestGetTables(object):

    @classmethod
    def setup_class(cls):

        if not pylons.config.get('ckan.datastore.read_url'):
            raise nose.SkipTest('Datastore runs on legacy mode, skipping...')

        engine = db._get_engine(
            {'connection_url': pylons.config['ckan.datastore.write_url']}
        )
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

        datastore_test_helpers.clear_db(cls.Session)

        create_tables = [
            'CREATE TABLE test_a (id_a text)',
            'CREATE TABLE test_b (id_b text)',
            'CREATE TABLE "TEST_C" (id_c text)',
        ]
        for create_table_sql in create_tables:
            cls.Session.execute(create_table_sql)

    @classmethod
    def teardown_class(cls):
        datastore_test_helpers.clear_db(cls.Session)

    def test_get_table_names(self):

        test_cases = [
            ('SELECT * FROM test_a', ['test_a']),
            ('SELECT * FROM public.test_a', ['test_a']),
            ('SELECT * FROM "TEST_C"', ['TEST_C']),
            ('SELECT * FROM public."TEST_C"', ['TEST_C']),
            ('SELECT * FROM pg_catalog.pg_database', ['pg_database']),
            ('SELECT rolpassword FROM pg_roles', ['pg_authid']),
            ('''SELECT p.rolpassword
                FROM pg_roles p
                JOIN test_b b
                ON p.rolpassword = b.id_b''', ['pg_authid', 'test_b']),
            ('''SELECT id_a, id_b, id_c
                FROM (
                    SELECT *
                    FROM (
                        SELECT *
                        FROM "TEST_C") AS c,
                        test_b) AS b,
                    test_a AS a''', ['test_a', 'test_b', 'TEST_C']),
            ('INSERT INTO test_a VALUES (\'a\')', ['test_a']),
        ]

        context = {
            'connection': self.Session.connection()
        }
        for case in test_cases:
            eq_(sorted(datastore_helpers.get_table_names_from_sql(context,
                                                                  case[0])),
                sorted(case[1]))
