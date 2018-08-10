# encoding: utf-8

from sqlalchemy import MetaData


def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    num_unmigrated = migrate_engine.execute('''
        SELECT count(*) FROM activity a JOIN package p ON a.object_id=p.id
        WHERE a.activity_type IN ('new package', 'changed package')
        AND a.data NOT LIKE '%%{"actor"%%'
        AND p.private = false;
    ''').fetchone()[0]
    if num_unmigrated:
        print('''
!!! NOTICE !!!
You should run the migrate_package_activity.py script to fully populate the
dataset dicts in the Activity Stream that admins can see. This can take a while
but can be run safely while CKAN is live, which is why this is not done
automatically as part of this 'paster db upgrade'.

Run migrate_package_activity.py like this:

  python ckan/migration/migrate_package_activity.py -c /etc/ckan/production.ini

NB This notice will not display again
        ''')
