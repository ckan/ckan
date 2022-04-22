# encoding: utf-8

import logging
import os

import click

from ckan.model import parse_db_config
from ckan.common import config

import ckanext.datastore as datastore_module
from ckanext.datastore.backend.postgres import identifier
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


def permissions_sql(maindb, datastoredb, mainuser, writeuser, readuser):
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
@click.option(u'--bom', is_flag=True)  # FIXME: options based on format
@click.pass_context
def dump(ctx, resource_id, output_file, format, offset, limit, bom):
    u'''Dump a datastore resource.
    '''
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        dump_to(
            resource_id,
            output_file,
            fmt=format,
            offset=offset,
            limit=limit,
            options={u'bom': bom},
            sort=u'_id',
            search_params={}
        )


def _parse_db_config(config_key=u'sqlalchemy.url'):
    db_config = parse_db_config(config_key)
    if not db_config:
        click.secho(
            u'Could not extract db details from url: %r' % config[config_key],
            fg=u'red',
            bold=True
        )
        raise click.Abort()
    return db_config
