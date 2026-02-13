# encoding: utf-8
from __future__ import annotations

from typing import Any
import sqlalchemy as sa
from sqlalchemy import orm

import ckan.model as model
from ckan.lib import search

import ckan.plugins as p
from ckan.tests.helpers import FunctionalTestBase, reset_db
import ckanext.datastore.backend.postgres as db


def extract(d, keys):
    return dict((k, d[k]) for k in keys if k in d)


def clear_db(Session):  # noqa
    drop_tables = """
        SELECT 'drop table "' || tablename || '" cascade;'
        FROM pg_tables WHERE schemaname = 'public'
        AND tablename != '_table_stats'"""
    c = Session.connection()
    results = c.execute(sa.text(drop_tables))
    for result in results:
        c.execute(sa.text(result[0]))

    drop_functions_sql = u"""
        SELECT 'drop function if exists ' || quote_ident(proname) || '();'
        FROM pg_proc
        INNER JOIN pg_namespace ns ON (pg_proc.pronamespace = ns.oid)
        WHERE ns.nspname = 'public' AND proname != 'populate_full_text_trigger'
        """
    drop_functions = u"".join(
        r[0] for r in c.execute(sa.text(drop_functions_sql))
    )
    if drop_functions:
        c.execute(sa.text(drop_functions))

    Session.commit()
    Session.remove()


def rebuild_all_dbs(Session):  # noqa
    """ If the tests are running on the same db, we have to make sure that
    the ckan tables are recreated.
    """
    db_read_url_parts = model.parse_db_config('ckan.datastore.write_url')
    db_ckan_url_parts = model.parse_db_config('sqlalchemy.url')
    same_db = db_read_url_parts["db_name"] == db_ckan_url_parts["db_name"]

    if same_db:
        model.repo.tables_created_and_initialised = False
    clear_db(Session)
    model.repo.rebuild_db()


def set_url_type(resources, user):
    context = {"user": user["name"]}
    for resource in resources:
        resource = p.toolkit.get_action("resource_show")(
            context, {"id": resource.id}
        )
        resource["url_type"] = "datastore"
        p.toolkit.get_action("resource_update")(context, resource)


def execute_sql(sql: str, params: dict[str, Any]):
    engine = db.get_write_engine()
    session = orm.scoped_session(orm.sessionmaker(bind=engine))
    return session.connection().execute(sa.text(sql), params)


def when_was_last_analyze(resource_id):
    results = execute_sql(
        """SELECT last_analyze
        FROM pg_stat_user_tables
        WHERE relname=:relname;
        """,
        {"relname": resource_id},
    ).fetchall()
    return results[0][0]


class DatastoreFunctionalTestBase(FunctionalTestBase):
    _load_plugins = (u"datastore",)

    @classmethod
    def setup_class(cls):
        engine = db.get_write_engine()
        rebuild_all_dbs(orm.scoped_session(orm.sessionmaker(bind=engine)))
        super(DatastoreFunctionalTestBase, cls).setup_class()


class DatastoreLegacyTestBase(object):
    u"""
    Tests that rely on data created in setup_class. No cleanup done between
    each test method. Not recommended for new tests.
    """

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded(u"datastore"):
            p.load(u"datastore")
        reset_db()
        search.clear_all()
        engine = db.get_write_engine()
        rebuild_all_dbs(orm.scoped_session(orm.sessionmaker(bind=engine)))

    @classmethod
    def teardown_class(cls):
        p.unload(u"datastore")
