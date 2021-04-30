# encoding: utf-8
import re
import mock

import pytest
import sqlalchemy.orm as orm
from sqlalchemy.exc import ProgrammingError

import ckanext.datastore.backend.postgres as db
import ckanext.datastore.backend.postgres as postgres_backend
import ckanext.datastore.helpers as datastore_helpers


class TestTypeGetters(object):
    def test_get_list(self):
        get_list = datastore_helpers.get_list
        assert get_list(None) is None
        assert get_list([]) == []
        assert get_list("") == []
        assert get_list("foo") == ["foo"]
        assert get_list("foo, bar") == ["foo", "bar"]
        assert get_list('foo_"bar, baz') == ['foo_"bar', "baz"]
        assert get_list('"foo", "bar"') == ["foo", "bar"]
        assert get_list(u"foo, bar") == ["foo", "bar"]
        assert get_list(["foo", "bar"]) == ["foo", "bar"]
        assert get_list([u"foo", u"bar"]) == ["foo", "bar"]
        assert get_list(["foo", ["bar", "baz"]]) == ["foo", ["bar", "baz"]]

    def test_is_single_statement(self):
        singles = [
            "SELECT * FROM footable",
            'SELECT * FROM "bartable"',
            'SELECT * FROM "bartable";',
            'SELECT * FROM "bart;able";',
            "select 'foo'||chr(59)||'bar'",
        ]

        multiples = [
            "SELECT * FROM abc; SET LOCAL statement_timeout to"
            "SET LOCAL statement_timeout to; SELECT * FROM abc",
            'SELECT * FROM "foo"; SELECT * FROM "abc"',
        ]

        for single in singles:
            assert postgres_backend.is_single_statement(single) is True

        for multiple in multiples:
            assert postgres_backend.is_single_statement(multiple) is False

    def test_should_fts_index_field_type(self):
        indexable_field_types = ["tsvector", "text", "number"]

        non_indexable_field_types = [
            "nested",
            "timestamp",
            "date",
            "_text",
            "text[]",
        ]

        for indexable in indexable_field_types:
            assert (
                datastore_helpers.should_fts_index_field_type(indexable)
                is True
            )

        for non_indexable in non_indexable_field_types:
            assert (
                datastore_helpers.should_fts_index_field_type(non_indexable)
                is False
            )


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
class TestGetTables(object):
    def test_get_table_names(self):
        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        create_tables = [
            u"CREATE TABLE test_a (id_a text)",
            u"CREATE TABLE test_b (id_b text)",
            u'CREATE TABLE "TEST_C" (id_c text)',
            u'CREATE TABLE test_d ("α/α" integer)',
        ]
        for create_table_sql in create_tables:
            session.execute(create_table_sql)

        test_cases = [
            (u"SELECT * FROM test_a", ["test_a"]),
            (u"SELECT * FROM public.test_a", ["test_a"]),
            (u'SELECT * FROM "TEST_C"', ["TEST_C"]),
            (u'SELECT * FROM public."TEST_C"', ["TEST_C"]),
            (u"SELECT * FROM pg_catalog.pg_database", ["pg_database"]),
            (u"SELECT rolpassword FROM pg_roles", ["pg_authid"]),
            (
                u"""SELECT p.rolpassword
                FROM pg_roles p
                JOIN test_b b
                ON p.rolpassword = b.id_b""",
                ["pg_authid", "test_b"],
            ),
            (
                u"""SELECT id_a, id_b, id_c
                FROM (
                    SELECT *
                    FROM (
                        SELECT *
                        FROM "TEST_C") AS c,
                        test_b) AS b,
                    test_a AS a""",
                ["test_a", "test_b", "TEST_C"],
            ),
            (u"INSERT INTO test_a VALUES ('a')", ["test_a"]),
            (u'SELECT "α/α" FROM test_d', ["test_d"]),
            (u'SELECT "α/α" FROM test_d WHERE "α/α" > 1000', ["test_d"]),
        ]

        context = {"connection": session.connection()}
        for case in test_cases:
            assert sorted(
                datastore_helpers.get_table_and_function_names_from_sql(context, case[0])[0]
            ) == sorted(case[1])


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
class TestGetFunctions(object):
    def test_get_function_names(self):

        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        create_tables = [
            u"CREATE TABLE test_a (id int, period date, subject_id text, result decimal)",
            u"CREATE TABLE test_b (name text, subject_id text)",
        ]
        for create_table_sql in create_tables:
            session.execute(create_table_sql)

        test_cases = [
            (u"SELECT max(id) from test_a", ["max"]),
            (u"SELECT count(distinct(id)) FROM test_a", ["count", "distinct"]),
            (u"SELECT trunc(avg(result),2) FROM test_a", ["trunc", "avg"]),
            (u"SELECT trunc(avg(result),2), avg(result) FROM test_a", ["trunc", "avg"]),
            (u"SELECT * from pg_settings", ["pg_show_all_settings"]),
            (u"SELECT * from pg_settings UNION SELECT * from pg_settings", ["pg_show_all_settings"]),
            (u"SELECT * from (SELECT * FROM pg_settings) AS tmp", ["pg_show_all_settings"]),
            (u"SELECT query_to_xml('SELECT max(id) FROM test_a', true, true , '')", ["query_to_xml"]),
            (u"select $$'$$, query_to_xml($X$SELECT table_name FROM information_schema.tables$X$,true,true,$X$$X$), $$'$$", ["query_to_xml"])
        ]

        context = {"connection": session.connection()}
        for case in test_cases:
            assert sorted(
                datastore_helpers.get_table_and_function_names_from_sql(context, case[0])[1]
            ) == sorted(case[1])

    def test_get_function_names_custom_function(self):

        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        create_tables = [
            u"""CREATE FUNCTION add(integer, integer) RETURNS integer
                AS 'select $1 + $2;'
                    LANGUAGE SQL
                        IMMUTABLE
                            RETURNS NULL ON NULL INPUT;
            """
        ]
        for create_table_sql in create_tables:
            session.execute(create_table_sql)

        context = {"connection": session.connection()}

        sql = "SELECT add(1, 2);"

        assert datastore_helpers.get_table_and_function_names_from_sql(context, sql)[1] == ["add"]

    def test_get_function_names_crosstab(self):
        """
        Crosstab functions need to be enabled in the database by executing the following using
        a super user:

            CREATE extension tablefunc;

        """

        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        create_tables = [
            u"CREATE TABLE test_a (id int, period date, subject_id text, result decimal)",
            u"CREATE TABLE test_b (name text, subject_id text)",
        ]
        for create_table_sql in create_tables:
            session.execute(create_table_sql)

        test_cases = [
            (
                u"""SELECT *
                FROM crosstab(
                    'SELECT extract(month from period)::text, test_b.name, trunc(avg(result),2)
                     FROM test_a, test_b
                     WHERE test_a.subject_id = test_b.subject_id')
                     AS final_result(month text, subject_1 numeric,subject_2 numeric);""",
                ['crosstab', 'final_result', 'extract', 'trunc', 'avg']
            ),
        ]

        context = {"connection": session.connection()}
        try:
            for case in test_cases:
                assert sorted(
                    datastore_helpers.get_table_and_function_names_from_sql(context, case[0])[1]
                ) == sorted(case[1])
        except ProgrammingError as e:
            if bool(re.search("function crosstab(.*) does not exist", str(e))):
                pytest.skip("crosstab functions not enabled in DataStore database")
