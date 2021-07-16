# encoding: utf-8

import logging
import os

import click

from ckan.model import parse_db_config
from ckan.common import config
import ckan.logic as logic

import ckanext.datastore as datastore_module
from ckanext.datastore.backend.postgres import identifier
from ckanext.datastore.blueprint import DUMP_FORMATS, dump_to

log = logging.getLogger(__name__)


@click.group(short_help="Perform commands to set up the datastore.")
def datastore():
    """Perform commands to set up the datastore.
    """
    pass


@datastore.command(
    'set-permissions',
    short_help='Generate SQL for permission configuration.'
)
def set_permissions():
    '''Emit an SQL script that will set the permissions for the datastore
    users as configured in your configuration file.'''

    write_url = _parse_db_config('ckan.datastore.write_url')
    read_url = _parse_db_config('ckan.datastore.read_url')
    db_url = _parse_db_config('sqlalchemy.url')

    # Basic validation that read and write URLs reference the same database.
    # This obviously doesn't check they're the same database (the hosts/ports
    # could be different), but it's better than nothing, I guess.

    if write_url['db_name'] != read_url['db_name']:
        click.secho(
            'The datastore write_url and read_url must refer to the same '
            'database!',
            fg='red',
            bold=True
        )
        raise click.Abort()

    sql = permissions_sql(
        maindb=db_url['db_name'],
        datastoredb=write_url['db_name'],
        mainuser=db_url['db_user'],
        writeuser=write_url['db_user'],
        readuser=read_url['db_user']
    )

    click.echo(sql)


def permissions_sql(maindb, datastoredb, mainuser, writeuser, readuser):
    template_filename = os.path.join(
        os.path.dirname(datastore_module.__file__), 'set_permissions.sql'
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
@click.argument('resource-id', nargs=1)
@click.argument(
    'output-file',
    type=click.File('wb'),
    default=click.get_binary_stream('stdout')
)
@click.option('--format', default='csv', type=click.Choice(DUMP_FORMATS))
@click.option('--offset', type=click.IntRange(0, None), default=0)
@click.option('--limit', type=click.IntRange(0))
@click.option('--bom', is_flag=True)  # FIXME: options based on format
@click.pass_context
def dump(ctx, resource_id, output_file, format, offset, limit, bom):
    '''Dump a datastore resource.
    '''
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        dump_to(
            resource_id,
            output_file,
            fmt=format,
            offset=offset,
            limit=limit,
            options={'bom': bom},
            sort='_id',
            search_params={}
        )


def _parse_db_config(config_key='sqlalchemy.url'):
    db_config = parse_db_config(config_key)
    if not db_config:
        click.secho(
            'Could not extract db details from url: %r' % config[config_key],
            fg='red',
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
    context = {'user': site_user['name']}

    result = logic.get_action('datastore_search')(
        context,
        {'resource_id': '_table_metadata'}
    )

    resource_id_list = []
    for record in result['records']:
        try:
            # ignore 'alias' records (views) as they are automatically
            # deleted when the parent resource table is dropped
            if record['alias_of']:
                continue

            # we need to do this to trigger resource_show auth function
            site_user = logic.get_action('get_site_user')(
                {'ignore_auth': True}, {})
            context = {'user': site_user['name']}

            logic.get_action('resource_show')(
                context,
                {'id': record['name']}
            )
        except logic.NotFound:
            resource_id_list.append(record['name'])
            click.echo("Resource '%s' orphaned - queued for drop" %
                       record['name'])
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
            context,
            {'resource_id': resource_id, 'force': True}
        )
        click.echo("Table '%s' dropped)" % resource_id)
        drop_count += 1

    click.echo('Dropped %s tables' % drop_count)


def get_commands():
    return (set_permissions, dump, purge)
