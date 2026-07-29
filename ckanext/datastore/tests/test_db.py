# encoding: utf-8

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
        ]
        for create_table_sql in create_tables:
            session.execute(sa.text(create_table_sql))

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
            session.execute(sa.text(create_table_sql))

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
            session.execute(sa.text(create_table_sql))

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
            session.execute(sa.text(create_table_sql))

        test_cases = [
            (u"""SELECT *
                FROM crosstab(
                    'SELECT extract(month from period)::text, test_b.name, trunc(avg(result),2)
                     FROM test_a, test_b
                     WHERE test_a.subject_id = test_b.subject_id')
                     AS final_result(month text, subject_1 numeric,subject_2 numeric);""",
                ['crosstab', 'final_result', 'extract', 'trunc', 'avg']),
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
