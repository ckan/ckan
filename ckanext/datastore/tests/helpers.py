# encoding: utf-8

from sqlalchemy import orm

import ckan.model as model
import ckan.lib.cli as cli
from ckan.lib import search

import ckan.plugins as p
from ckan.tests.helpers import FunctionalTestBase, reset_db
import ckanext.datastore.backend.postgres as db


def extract(d, keys):
    return dict((k, d[k]) for k in keys if k in d)


def clear_db(Session):
    drop_tables = u'''select 'drop table "' || tablename || '" cascade;'
                    from pg_tables where schemaname = 'public' '''
    c = Session.connection()
    results = c.execute(drop_tables)
    for result in results:
        c.execute(result[0])

    drop_functions_sql = u'''
        SELECT 'drop function ' || quote_ident(proname) || '();'
        FROM pg_proc
        INNER JOIN pg_namespace ns ON (pg_proc.pronamespace = ns.oid)
        WHERE ns.nspname = 'public' AND proname != 'populate_full_text_trigger'
        '''
    drop_functions = u''.join(r[0] for r in c.execute(drop_functions_sql))
    if drop_functions:
        c.execute(drop_functions)

    Session.commit()
    Session.remove()


def rebuild_all_dbs(Session):
    ''' If the tests are running on the same db, we have to make sure that
    the ckan tables are recrated.
    '''
    db_read_url_parts = cli.parse_db_config('ckan.datastore.write_url')
    db_ckan_url_parts = cli.parse_db_config('sqlalchemy.url')
    same_db = db_read_url_parts['db_name'] == db_ckan_url_parts['db_name']

    if same_db:
        model.repo.tables_created_and_initialised = False
    clear_db(Session)
    model.repo.rebuild_db()


def set_url_type(resources, user):
    context = {'user': user.name}
    for resource in resources:
        resource = p.toolkit.get_action('resource_show')(
            context, {'id': resource.id})
        resource['url_type'] = 'datastore'
        p.toolkit.get_action('resource_update')(context, resource)


class DatastoreFunctionalTestBase(FunctionalTestBase):
    _load_plugins = (u'datastore', )

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
        p.load(u'datastore')
        reset_db()
        search.clear_all()
        engine = db.get_write_engine()
        rebuild_all_dbs(orm.scoped_session(orm.sessionmaker(bind=engine)))

    @classmethod
    def teardown_class(cls):
        p.unload(u'datastore')
