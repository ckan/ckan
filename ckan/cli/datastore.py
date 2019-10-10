# encoding: utf-8

import logging
import os
import re

import click

from ckan.cli import error_shout
from ckan.common import config

import ckanext.datastore as datastore_module
from ckanext.datastore.backend.postgres import identifier
from ckanext.datastore.view import DUMP_FORMATS, dump_to

log = logging.getLogger(__name__)


@click.group()
def datastore():
    u'''Perform commands to set up the datastore.
    '''


@datastore.command(
    u'set-permissions',
    short_help=u'Generate SQL for permission configuration.'
)
def set_permissions():
    u'''Emit an SQL script that will set the permissions for the datastore
    users as configured in your configuration file.'''

    write_url = parse_db_config(u'ckan.datastore.write_url')
    read_url = parse_db_config(u'ckan.datastore.read_url')
    db_url = parse_db_config(u'sqlalchemy.url')

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
    flask_app = ctx.obj.app.apps[u'flask_app']._wsgi_app
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


def parse_db_config(config_key=u'sqlalchemy.url'):
    u''' Takes a config key for a database connection url and parses it into
    a dictionary. Expects a url like:

    'postgres://tester:pass@localhost/ckantest3'
    '''
    url = config[config_key]
    regex = [
        u'^\\s*(?P<db_type>\\w*)', u'://', u'(?P<db_user>[^:]*)', u':?',
        u'(?P<db_pass>[^@]*)', u'@', u'(?P<db_host>[^/:]*)', u':?',
        u'(?P<db_port>[^/]*)', u'/', u'(?P<db_name>[\\w.-]*)'
    ]
    db_details_match = re.match(u''.join(regex), url)
    if not db_details_match:
        click.secho(
            u'Could not extract db details from url: %r' % url,
            fg=u'red',
            bold=True
        )
        raise click.Abort()
    db_details = db_details_match.groupdict()
    return db_details
