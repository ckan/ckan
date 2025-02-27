# encoding: utf-8

from typing import Any
import logging
import os
import json

import click

from ckan.model import parse_db_config
from ckan.common import config
import ckan.logic as logic

import ckanext.datastore as datastore_module
from ckanext.datastore.backend import get_all_resources_ids_in_datastore
from ckanext.datastore.backend.postgres import (
    identifier,
    literal_string,
    get_read_engine,
    get_write_engine,
    _get_raw_field_info,
    _TIMEOUT,
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

    resource_id_list = []
    for resid in get_all_resources_ids_in_datastore():
        try:
            logic.get_action('resource_show')(
                {'user': site_user['name']},
                {'id': resid}
            )
        except logic.NotFound:
            resource_id_list.append(resid)
            click.echo("Resource '%s' orphaned - queued for drop" %
                       resid)
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

    count = 0
    skipped = 0
    noinfo = 0
    read_connection = get_read_engine().connect()
    for resid in get_all_resources_ids_in_datastore():
        raw_fields, old = _get_raw_field_info(read_connection, resid)
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
                    identifier(resid),
                    identifier(fid),
                    raw_sql))

            if alter_sql:
                connection.exec_driver_sql(';'.join(alter_sql))
                count += 1
            else:
                noinfo += 1

    click.echo('Upgraded %d tables (%d already upgraded, %d no info)' % (
        count, skipped, noinfo))


@datastore.command(
    'fts-index',
    short_help='create or remove full-text search indexes after changing '
    'the ckan.datastore.default_fts_index_field_types setting'
)
@click.option(
    '--timeout', metavar='SECONDS',
    type=click.FloatRange(0, 2147483.647),  # because postgres max int
    default=_TIMEOUT / 1000, show_default=True,
    help='maximum index creation time in seconds',
)
def fts_index(timeout: float):
    '''Use to create or remove full-text search indexes after changing
    the ckan.datastore.default_fts_index_field_types setting.
    '''
    site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})
    resource_ids = get_all_resources_ids_in_datastore()

    for i, resid in enumerate(get_all_resources_ids_in_datastore(), 1):
        print(f'\r{resid} [{i}/{len(resource_ids)}] ...', end='')
        logic.get_action('datastore_create')(
            {'user': site_user['name'],
             'query_timeout': int(timeout * 1000)},  # type: ignore
            {'resource_id': resid, 'force': True}
        )
    print('\x08\x08\x08done')


def get_commands():
    return (set_permissions, dump, purge, upgrade)
