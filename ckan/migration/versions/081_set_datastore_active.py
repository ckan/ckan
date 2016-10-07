# encoding: utf-8

import json
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from ckan.common import config


def upgrade(migrate_engine):

    datastore_connection_url = config.get(
        'ckan.datastore.read_url', config.get('ckan.datastore.write_url'))

    if not datastore_connection_url:
        return

    try:
        datastore_engine = create_engine(datastore_connection_url)
    except SQLAlchemyError:
        return

    try:
        datastore_connection = datastore_engine.connect()
    except SQLAlchemyError:
        datastore_engine.dispose()
        return

    try:

        resources_in_datastore = datastore_connection.execute('''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name != '_table_metadata'
        ''')

        if resources_in_datastore.rowcount:

            resources = migrate_engine.execute('''
                SELECT id, extras
                FROM resource
                WHERE id IN ({0}) AND extras IS NOT NULL
            '''.format(
                ','.join(['\'{0}\''.format(_id[0])
                          for _id
                          in resources_in_datastore])
                )
            )
            if resources.rowcount:
                params = []
                for resource in resources:
                    new_extras = json.loads(resource[1])
                    new_extras.update({'datastore_active': True})
                    params.append(
                        {'id': resource[0],
                         'extras': json.dumps(new_extras)})

                migrate_engine.execute(
                    text('''
                    UPDATE resource
                    SET extras = :extras
                    WHERE id = :id'''),
                    params)
    finally:
        datastore_connection.close()
        datastore_engine.dispose()
