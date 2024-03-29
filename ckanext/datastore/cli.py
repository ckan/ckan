# encoding: utf-8

from typing import Any
import logging
import os
import json

import click
import sqlalchemy as sa

from ckan.model import parse_db_config
from ckan.common import config
import ckan.logic as logic

import ckanext.datastore as datastore_module
from ckanext.datastore.backend.postgres import (
    identifier,
    literal_string,
    get_read_engine,
    get_write_engine,
    _get_raw_field_info,
)
from ckanext.datastore.blueprint import DUMP_FORMATS, dump_to

log = logging.getLogger(__name__)


@click.group(short_help=u"Perform commands to set up the datastore.")
def datastore():
    """Perform commands to set up the datastore.
    """
    pass


@datastore.command(
    u'set-permissions',
    short_help=u'Generate SQL for permission configuration.'
)
def set_permissions():
    u'''Emit an SQL script that will set the permissions for the datastore
    users as configured in your configuration file.'''

    write_url = _parse_db_config(u'ckan.datastore.write_url')
    read_url = _parse_db_config(u'ckan.datastore.read_url')
    db_url = _parse_db_config(u'sqlalchemy.url')

    # Basic validation that read and write URLs reference the same database.
    # This obviously doesn't check they're the same database (the hosts/ports
    # could be different), but it's better than nothing, I guess.

    if write_url[u'db_name'] != read_url[u'db_name']:
        click.secho(
            u'The datastore write_url and read_url must refer to the same '
            u'database!',
            fg=u'red',
            bold=True
        )
        raise click.Abort()

    sql = permissions_sql(
        maindb=db_url[u'db_name'],
        datastoredb=write_url[u'db_name'],
        mainuser=db_url[u'db_user'],
        writeuser=write_url[u'db_user'],
        readuser=read_url[u'db_user']
    )

    click.echo(sql)


def permissions_sql(maindb: str, datastoredb: str, mainuser: str,
                    writeuser: str, readuser: str):
    template_filename = os.path.join(
        os.path.dirname(datastore_module.__file__), u'set_permissions.sql'
    )
    with open(template_filename) as fp:
        template = fp.read()
    return template.format(
        maindb=identifier(maindb),
        datastoredb=identifier(datastoredb),
        mainuser=identifier(mainuser),
        writeuser=identifier(writeuser),
        readuser=identifier(readuser)
    )


@datastore.command()
@click.argument(u'resource-id', nargs=1)
@click.argument(
    u'output-file',
    type=click.File(u'wb'),
    default=click.get_binary_stream(u'stdout')
)
@click.option(u'--format', default=u'csv', type=click.Choice(DUMP_FORMATS))
@click.option(u'--offset', type=click.IntRange(0, None), default=0)
@click.option(u'--limit', type=click.IntRange(0))
@click.option(u'--bom', is_flag=True)
@click.pass_context
def dump(ctx: Any, resource_id: str, output_file: Any, format: str,
         offset: int, limit: int, bom: bool):
    u'''Dump a datastore resource.
    '''
    flask_app = ctx.meta['flask_app']
    user = logic.get_action('get_site_user')(
            {'ignore_auth': True}, {})
    with flask_app.test_request_context():
        for block in dump_to(resource_id,
                             fmt=format,
                             offset=offset,
                             limit=limit,
                             options={u'bom': bom},
                             sort=u'_id',
                             search_params={},
                             user=user['name']):
            output_file.write(block)


def _parse_db_config(config_key: str = u'sqlalchemy.url'):
    db_config = parse_db_config(config_key)
    if not db_config:
        click.secho(
            u'Could not extract db details from url: %r' % config[config_key],
            fg=u'red',
            bold=True
        )
        raise click.Abort()
    return db_config


@datastore.command(
    'purge',
    short_help='purge orphaned resources from the datastore.'
)
def purge():
    '''Purge orphaned resources from the datastore using the datastore_delete
    action, which drops tables when called without filters.'''

    site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})

    result = logic.get_action('datastore_search')(
        {'user': site_user['name']},
        {'resource_id': '_table_metadata'}
    )

    resource_id_list = []
    for record in result['records']:
        try:
            # ignore 'alias' records (views) as they are automatically
            # deleted when the parent resource table is dropped
            if record['alias_of']:
                continue

            logic.get_action('resource_show')(
                {'user': site_user['name']},
                {'id': record['name']}
            )
        except logic.NotFound:
            resource_id_list.append(record['name'])
            click.echo("Resource '%s' orphaned - queued for drop" %
                       record[u'name'])
        except KeyError:
            continue

    orphaned_table_count = len(resource_id_list)
    click.echo('%d orphaned tables found.' % orphaned_table_count)

    if not orphaned_table_count:
        return

    click.confirm('Proceed with purge?', abort=True)

    # Drop the orphaned datastore tables. When datastore_delete is called
    # without filters, it does a drop table cascade
    drop_count = 0
    for resource_id in resource_id_list:
        logic.get_action('datastore_delete')(
            {'user': site_user['name']},
            {'resource_id': resource_id, 'force': True}
        )
        click.echo("Table '%s' dropped)" % resource_id)
        drop_count += 1

    click.echo('Dropped %s tables' % drop_count)


@datastore.command(
    'upgrade',
    short_help='upgrade datastore field info for plugin_data support'
)
def upgrade():
    '''Move field info to _info so that plugins may add private information
    to each field for their own purposes.'''

    site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})

    result = logic.get_action('datastore_search')(
        {'user': site_user['name']},
        {'resource_id': '_table_metadata'}
    )

    count = 0
    skipped = 0
    noinfo = 0
    read_connection = get_read_engine()
    for record in result['records']:
        if record['alias_of']:
            continue

        raw_fields, old = _get_raw_field_info(read_connection, record['name'])
        if not old:
            if not raw_fields:
                noinfo += 1
            else:
                skipped += 1
            continue

        alter_sql = []
        with get_write_engine().begin() as connection:
            for fid, fvalue in raw_fields.items():
                raw = {'_info': fvalue}
                # ' ' prefix for data version
                raw_sql = literal_string(' ' + json.dumps(
                    raw, ensure_ascii=False, separators=(',', ':')))
                alter_sql.append(u'COMMENT ON COLUMN {0}.{1} is {2}'.format(
                    identifier(record['name']),
                    identifier(fid),
                    raw_sql))

            if alter_sql:
                connection.execute(sa.text(';'.join(alter_sql)))
                count += 1
            else:
                noinfo += 1

    click.echo('Upgraded %d tables (%d already upgraded, %d no info)' % (
        count, skipped, noinfo))


def get_commands():
    return (set_permissions, dump, purge, upgrade)
