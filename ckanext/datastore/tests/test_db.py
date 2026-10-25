# encoding: utf-8

import json
import uuid
import unittest.mock as mock
import pytest

import sqlalchemy as sa
import sqlalchemy.orm as orm

import ckan.lib.jobs as jobs
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.datastore.backend as backend
import ckanext.datastore.backend.postgres as db


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("with_plugins")
class TestCreateIndexes(object):
    def test_creates_fts_index_using_gist_by_default(self):
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id}

        db.create_indexes(context, data_dict)

        self._assert_created_index_on(
            "_full_text", connection, resource_id, method="gist"
        )

    @pytest.mark.ckan_config("ckan.datastore.default_fts_index_method", "gin")
    def test_default_fts_index_method_can_be_overwritten_by_config_var(self):
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id}

        db.create_indexes(context, data_dict)

        self._assert_created_index_on(
            "_full_text", connection, resource_id, method="gin"
        )

    @pytest.mark.ckan_config(
        "ckan.datastore.default_fts_index_field_types", "text tsvector")
    @mock.patch("ckanext.datastore.backend.postgres._get_fields")
    def test_creates_fts_index_on_all_fields_except_dates_nested_and_arrays_with_english_as_default(
        self, _get_fields
    ):
        _get_fields.return_value = [
            {"id": "text", "type": "text"},
            {"id": "tsvector", "type": "tsvector"},
            {"id": "nested", "type": "nested"},
            {"id": "date", "type": "date"},
            {"id": "text array", "type": "text[]"},
            {"id": "timestamp", "type": "timestamp"},
        ]
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id}

        db.create_indexes(context, data_dict)

        self._assert_created_index_on(
            "text", connection, resource_id, "english"
        )
        self._assert_created_index_on(
            "tsvector", connection, resource_id,
        )

    @mock.patch("ckanext.datastore.backend.postgres._get_fields")
    def test_creates_no_fts_indexes_by_default(
        self, _get_fields
    ):
        _get_fields.return_value = [
            {"id": "text", "type": "text"},
            {"id": "tsvector", "type": "tsvector"},
            {"id": "nested", "type": "nested"},
            {"id": "date", "type": "date"},
            {"id": "text array", "type": "text[]"},
            {"id": "timestamp", "type": "timestamp"},
        ]
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id}

        db.create_indexes(context, data_dict)

        self._assert_no_index_created_on(
            "text", connection, resource_id, "english"
        )
        self._assert_no_index_created_on(
            "tsvector", connection, resource_id,
        )

    @pytest.mark.ckan_config(
        "ckan.datastore.default_fts_index_field_types", "text tsvector")
    @pytest.mark.ckan_config("ckan.datastore.default_fts_lang", "simple")
    @mock.patch("ckanext.datastore.backend.postgres._get_fields")
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_with_config_var(
        self, _get_fields
    ):
        _get_fields.return_value = [{"id": "foo", "type": "text"}]
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id}

        db.create_indexes(context, data_dict)

        self._assert_created_index_on("foo", connection, resource_id, "simple")

    @pytest.mark.ckan_config(
        "ckan.datastore.default_fts_index_field_types", "text tsvector")
    @pytest.mark.ckan_config("ckan.datastore.default_fts_lang", "simple")
    @mock.patch("ckanext.datastore.backend.postgres._get_fields")
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_using_lang_param(
        self, _get_fields
    ):
        _get_fields.return_value = [{"id": "foo", "type": "text"}]
        connection = mock.MagicMock()
        context = {"connection": connection}
        resource_id = "resource_id"
        data_dict = {"resource_id": resource_id, "language": "french"}

        db.create_indexes(context, data_dict)

        self._assert_created_index_on("foo", connection, resource_id, "french")

    def _assert_created_index_on(
        self,
        field,
        connection,
        resource_id,
        lang=None,
        cast=False,
        method="gist",
    ):
        field = u'"{0}"'.format(field)
        if cast:
            field = u"cast({0} AS text)".format(field)
        if lang is not None:
            sql_str = (
                u'ON "resource_id" '
                u"USING {method}(to_tsvector('{lang}', {field}))"
            )
            sql_str = sql_str.format(method=method, lang=lang, field=field)
        else:
            sql_str = u"USING {method}({field})".format(
                method=method, field=field
            )

        calls = connection.execute.call_args_list

        was_called = any(sql_str in str(call.args[0]) for call in calls)

        assert was_called, (
            "Expected 'connection.execute' to have been "
            "called with a string containing '%s'" % sql_str
        )

    def _assert_no_index_created_on(
        self,
        field,
        connection,
        resource_id,
        lang=None,
        cast=False,
        method="gist",
    ):
        field = u'"{0}"'.format(field)
        if cast:
            field = u"cast({0} AS text)".format(field)
        if lang is not None:
            sql_str = (
                u'ON "resource_id" '
                u"USING {method}(to_tsvector('{lang}', {field}))"
            )
            sql_str = sql_str.format(method=method, lang=lang, field=field)
        else:
            sql_str = u"USING {method}({field})".format(
                method=method, field=field
            )

        calls = connection.execute.call_args_list

        was_called = any(sql_str in str(call.args[0]) for call in calls)

        assert not was_called, (
            "Expected 'connection.execute' to not have been "
            "called with a string containing '%s'" % sql_str
        )


class TestGetAllResourcesIdsInDatastore(object):
    @pytest.mark.ckan_config(u"ckan.plugins", u"datastore")
    @pytest.mark.usefixtures(u"with_plugins", u"clean_db")
    def test_get_all_resources_ids_in_datastore(self):
        resource_in_datastore = factories.Resource()
        resource_not_in_datastore = factories.Resource()
        data = {"resource_id": resource_in_datastore["id"], "force": True}
        helpers.call_action("datastore_create", **data)

        resource_ids = backend.get_all_resources_ids_in_datastore()

        assert resource_in_datastore["id"] in resource_ids
        assert resource_not_in_datastore["id"] not in resource_ids


def datastore_job(res_id, value):
    """
    A background job that uses the Datastore.
    """
    app = helpers._get_test_app()
    if not p.plugin_loaded(u"datastore"):
        p.load("datastore")
    data = {
        "resource_id": res_id,
        "method": "insert",
        "records": [{"value": value}],
    }

    with app.flask_app.test_request_context():
        helpers.call_action("datastore_upsert", **data)


class TestBackgroundJobs(helpers.RQTestBase):
    """
    Test correct interaction with the background jobs system.
    """
    @pytest.mark.ckan_config(u"ckan.plugins", u"datastore")
    @pytest.mark.usefixtures(u"with_plugins", u"clean_db")
    def test_worker_datastore_access(self, app):
        """
        Test DataStore access from within a worker.
        """
        pkg = factories.Dataset()
        data = {
            "resource": {"package_id": pkg["id"]},
            "fields": [{"id": "value", "type": "int"}],
        }

        table = helpers.call_action("datastore_create", **data)
        res_id = table["resource_id"]
        for i in range(3):
            self.enqueue(datastore_job, args=[res_id, i])
        jobs.Worker().work(burst=True)
        # Aside from ensuring that the job succeeded, this also checks
        # that accessing the Datastore still works in the main process.
        result = helpers.call_action("datastore_search", resource_id=res_id)
        assert [0, 1, 2] == [r["value"] for r in result["records"]]


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
class TestGetTables(object):
    def test_get_table_names(self):
        engine = db.get_write_engine()
        session = orm.scoped_session(orm.sessionmaker(bind=engine))
        create_tables = [
            "CREATE TABLE test_a (id_a text)",
            "CREATE TABLE test_b (id_b text)",
            'CREATE TABLE "TEST_C" (id_c text)',
            'CREATE TABLE test_d ("α/α" integer)',
            "CREATE VIEW test_e AS SELECT * from test_a INNER JOIN test_b ON id_a = id_b"
        ]
        for create_table_sql in create_tables:
            session.execute(sa.text(create_table_sql))

        test_cases = [
            ("SELECT * FROM test_a", {(None, "test_a")}),
            ("SELECT * FROM public.test_a", {("public", "test_a")}),
            ('SELECT * FROM "TEST_C"', {(None, "TEST_C")}),
            ('SELECT * FROM public."TEST_C"', {("public", "TEST_C")}),
            ("SELECT * from test_e", {("public", "test_a"), ("public", "test_b")}),
            ("SELECT * FROM pg_catalog.pg_database", {("pg_catalog", "pg_database")}),
            ("SELECT rolpassword FROM pg_roles", {(None, "pg_roles")}),
            (
                """SELECT p.rolpassword
                FROM pg_roles p
                JOIN test_b b
                ON p.rolpassword = b.id_b""",
                {(None, "pg_roles"), (None, "test_b")},
            ),
            (
                """SELECT id_a, id_b, id_c
                FROM (
                    SELECT *
                    FROM (
                        SELECT *
                        FROM "TEST_C") AS c,
                        test_b) AS b,
                    test_a AS a""",
                {(None, "test_a"), (None, "test_b"), (None, "TEST_C")},
            ),
            ('SELECT "α/α" FROM test_d', {(None, "test_d")}),
            ('SELECT "α/α" FROM test_d WHERE "α/α" > 1000', {(None, "test_d")}),
        ]

        for case in test_cases:
            assert db.sanitize_sql(session.connection(), case[0])[1] == case[1]


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
            session.execute(sa.text(create_table_sql))

        test_cases = [
            (u"SELECT max(id) from test_a", ["max"]),
            (u"SELECT count(distinct(id)) FROM test_a", ["count"]),
            (u"SELECT trunc(avg(result),2) FROM test_a", ["trunc", "avg"]),
            (u"SELECT trunc(avg(result),2), avg(result) FROM test_a", ["trunc", "avg"]),
            (u"SELECT query_to_xml('SELECT max(id) FROM test_a', true, true , '')", ["query_to_xml"]),
            (u"select $$'$$, query_to_xml($X$SELECT table_name FROM information_schema.tables$X$,true,true,$X$$X$), $$'$$", ["query_to_xml"])
        ]

        for case in test_cases:
            assert db.sanitize_sql(session.connection(), case[0])[2] == {(name,) for name in case[1]}

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
            session.execute(sa.text(create_table_sql))

        sql = "SELECT add(1, 2);"

        assert db.sanitize_sql(session.connection(), sql)[2] == {("add",)}


@pytest.fixture
def load_records_table():
    session = orm.sessionmaker(bind=db.get_write_engine())()
    table_name = "datastore_insert_test_" + uuid.uuid4().hex
    yield session, table_name
    session.rollback()
    session.execute(sa.text(
        f'DROP TABLE IF EXISTS public."{table_name}"'
    ))
    session.commit()
    session.close()


@pytest.mark.ckan_config("ckan.plugins", "datastore")
@pytest.mark.usefixtures("with_plugins")
class TestLoadRecords(object):
    def test_inserts_array_rows_and_returns_all_fields(
        self, load_records_table
    ):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                id serial PRIMARY KEY,
                name text NOT NULL,
                amount integer DEFAULT 42,
                details jsonb DEFAULT '{{}}'::jsonb,
                note text
            )""")
        )

        result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['name'],
                ARRAY[['Ada, Lovelace'], ['Bob']]::text[][]
            )"""),
            {"table_name": table_name},
        ).scalar()

        assert json.loads(result) == {
            "records": [
                ["1", "Ada, Lovelace", "42", "{}", None],
                ["2", "Bob", "42", "{}", None],
            ],
            "fields": ["id", "name", "amount", "details", "note"],
        }

    def test_collects_errors_and_rolls_back_inserted_rows(
        self, load_records_table
    ):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                id integer,
                CONSTRAINT datastore_insert_test_pkey PRIMARY KEY (id),
                amount integer NOT NULL
            )""")
        )

        errors = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['id', 'amount'],
                ARRAY[['1', '10'], ['1', '20'], ['3', 'not-an-integer']]::text[][]
            )"""),
            {"table_name": table_name},
        ).scalar()

        errors = json.loads(errors)
        assert errors == [
            [1, 'duplicate key value violates unique constraint '
                '"datastore_insert_test_pkey"'],
            [2, 'invalid input syntax for type integer: "not-an-integer"']
        ]
        assert session.execute(sa.text(
            f"SELECT count(*) FROM {table_name}"
        )).scalar() == 0

    def test_empty_strings_become_null_only_for_non_text_fields(
        self, load_records_table
    ):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                amount integer,
                details jsonb,
                name text
            )""")
        )

        result = session.execute(sa.text(
            """SELECT load_records(
                :table_name,
                ARRAY['amount', 'details', 'name'],
                ARRAY[['', '', '']]::text[][]
            )"""),
            {"table_name": table_name},
        ).scalar()

        assert json.loads(result)["records"] == [
            [None, None, ""],
        ]

    def test_can_return_first_error_only(self, load_records_table):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                id integer,
                CONSTRAINT datastore_insert_test_pkey PRIMARY KEY (id),
                amount integer NOT NULL
            )""")
        )

        errors = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['id', 'amount'],
                ARRAY[['1', '10'], ['1', '20'], ['3', 'not-an-integer']]::text[][],
                true
            )"""),
            {"table_name": table_name},
        ).scalar()

        errors = json.loads(errors)
        assert [row_number for row_number, _ in errors] == [1]
        assert session.execute(sa.text(
            f"SELECT count(*) FROM {table_name}"
        )).scalar() == 0

    def test_can_skip_returning_records(self, load_records_table):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                name text
            )""")
        )

        result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['name'],
                ARRAY[['Ada'], ['Bob']]::text[][],
                false, false
            )"""),
            {"table_name": table_name},
        ).scalar()

        result = json.loads(result)
        assert result == {"records": None, "fields": ["name"]}
        assert session.execute(sa.text(
            f"SELECT count(*) FROM {table_name}"
        )).scalar() == 2

    def test_update_and_upsert_match_unique_constraint(self, load_records_table):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                _id serial PRIMARY KEY,
                code text NOT NULL,
                region text NOT NULL,
                amount integer NOT NULL,
                CONSTRAINT {table_name}_code_region_key UNIQUE (code, region)
            )"""
        ))
        session.execute(sa.text(
            f"INSERT INTO {table_name} (code, region, amount) "
            "VALUES ('alpha', 'north', 10)"
        ))

        unique_columns = session.execute(sa.text(
            "SELECT first_unique_constraint_columns(:table_name)"
        ), {"table_name": table_name}).scalar()
        assert list(unique_columns) == ["code", "region"]

        unmatched_update = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['_id', 'amount', 'region', 'code'],
                ARRAY[['99', '20', 'north', 'alpha']]::text[][],
                false, true, 'update'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(unmatched_update) == [
            [0, "No matching record found for update"]
        ]

        update_result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['_id', 'amount', 'region', 'code'],
                ARRAY[['1', '20', 'north', 'alpha']]::text[][],
                false, true, 'update'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(update_result)["records"] == [
            ["1", "alpha", "north", "20"]
        ]

        upsert_result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['code', 'region', 'amount'],
                ARRAY[['alpha', 'north', '30'], ['beta', 'south', '40']]::text[][],
                false, true, 'upsert'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(upsert_result)["records"] == [
            ["1", "alpha", "north", "30"],
            ["3", "beta", "south", "40"],
        ]

        no_records_result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['code', 'region', 'amount'],
                ARRAY[['alpha', 'north', '50']]::text[][],
                false, false, 'upsert'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(no_records_result) == {
            "records": None,
            "fields": ["_id", "code", "region", "amount"],
        }
        assert session.execute(sa.text(
            f"SELECT amount FROM {table_name} WHERE _id = 1"
        )).scalar() == 50

        update_result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['code', 'region', 'amount'],
                ARRAY[
                    ['alpha', 'north', '60'],
                    ['beta', 'south', '70']
                ]::text[][],
                false, true, 'update'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(update_result)["records"] == [
            ["1", "alpha", "north", "60"],
            ["3", "beta", "south", "70"],
        ]

        no_records_update = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['code', 'region', 'amount'],
                ARRAY[['alpha', 'north', '80']]::text[][],
                false, false, 'update'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(no_records_update) == {
            "records": None,
            "fields": ["_id", "code", "region", "amount"],
        }
        assert session.execute(sa.text(
            f"SELECT amount FROM {table_name} WHERE _id = 1"
        )).scalar() == 80

    def test_id_is_the_only_upsert_conflict_target(self, load_records_table):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                _id integer PRIMARY KEY,
                code text NOT NULL,
                region text NOT NULL,
                amount integer NOT NULL,
                CONSTRAINT {table_name}_code_region_key UNIQUE (code, region)
            )"""
        ))
        session.execute(sa.text(
            f"INSERT INTO {table_name} VALUES (1, 'alpha', 'north', 10)"
        ))

        errors = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['_id', 'code', 'region', 'amount'],
                ARRAY[['99', 'alpha', 'north', '20']]::text[][],
                false, true, 'upsert'
            )"""
        ), {"table_name": table_name}).scalar()

        errors = json.loads(errors)
        assert errors[0][0] == 0
        assert errors[0][1].startswith(
            "duplicate key value violates unique constraint"
        )
        assert session.execute(sa.text(
            f"SELECT _id, amount FROM {table_name}"
        )).all() == [(1, 10)]

    @pytest.mark.parametrize("operation", ["update", "upsert"])
    def test_repeated_keys_return_bulk_error(
        self, load_records_table, operation
    ):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                _id integer PRIMARY KEY,
                value integer NOT NULL
            )"""
        ))
        session.execute(sa.text(
            f"INSERT INTO {table_name} VALUES (1, 10)"
        ))

        result = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['_id', 'value'],
                ARRAY[['1', '20'], ['1', '30']]::text[][],
                false, true, :operation
            )"""
        ), {"table_name": table_name, "operation": operation}).scalar()

        errors = json.loads(result)
        assert [row_number for row_number, _ in errors] == [0]
        assert session.execute(sa.text(
            f"SELECT value FROM {table_name} WHERE _id = 1"
        )).scalar() == 10

    def test_update_returns_error_for_unmatched_row(self, load_records_table):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"""CREATE TABLE {table_name} (
                _id serial PRIMARY KEY,
                value text NOT NULL
            )"""
        ))

        errors = session.execute(sa.text(
            """SELECT load_records(
                :table_name, ARRAY['_id', 'value'],
                ARRAY[['99', 'missing']]::text[][],
                false, true, 'update'
            )"""
        ), {"table_name": table_name}).scalar()
        assert json.loads(errors) == [[0, "No matching record found for update"]]

    @pytest.mark.parametrize("operation", ["update", "upsert"])
    def test_update_and_upsert_require_key_fields(
        self, load_records_table, operation
    ):
        session, table_name = load_records_table
        session.execute(sa.text(
            f"CREATE TABLE {table_name} (value text NOT NULL)"
        ))

        with pytest.raises(sa.exc.DBAPIError, match="No key fields provided"):
            session.execute(sa.text(
                """SELECT load_records(
                    :table_name, ARRAY['value'],
                    ARRAY[['missing']]::text[][],
                    false, true, :operation
                )"""
            ), {"table_name": table_name, "operation": operation})
