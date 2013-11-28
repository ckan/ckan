import ckan.model as model
import ckan.lib.cli as cli

import ckan.plugins as p


def extract(d, keys):
    return dict((k, d[k]) for k in keys if k in d)


def clear_db(Session):
    drop_tables = u'''select 'drop table "' || tablename || '" cascade;'
                    from pg_tables where schemaname = 'public' '''
    c = Session.connection()
    results = c.execute(drop_tables)
    for result in results:
        c.execute(result[0])
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
