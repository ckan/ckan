# encoding: utf-8

import os

from ckan.lib.cli import (
    load_config,
    parse_db_config,
    paster_click_group,
    click_config_option,
)
from ckanext.datastore.backend.postgres import identifier
from ckanext.datastore.controller import DUMP_FORMATS, dump_to

import click


datastore_group = paster_click_group(
    summary=u'Perform commands to set up the datastore')


@datastore_group.command(
    u'set-permissions',
    help=u'Emit an SQL script that will set the permissions for the '
         u'datastore users as configured in your configuration file.')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.pass_context
def set_permissions(ctx, config):
    load_config(config or ctx.obj['config'])

    write_url = parse_db_config(u'ckan.datastore.write_url')
    read_url = parse_db_config(u'ckan.datastore.read_url')
    db_url = parse_db_config(u'sqlalchemy.url')

    # Basic validation that read and write URLs reference the same database.
    # This obviously doesn't check they're the same database (the hosts/ports
    # could be different), but it's better than nothing, I guess.
    if write_url['db_name'] != read_url['db_name']:
        exit(u"The datastore write_url and read_url must refer to the same "
             u"database!")

    sql = permissions_sql(
        maindb=db_url['db_name'],
        datastoredb=write_url['db_name'],
        mainuser=db_url['db_user'],
        writeuser=write_url['db_user'],
        readuser=read_url['db_user'])

    print(sql)


def permissions_sql(maindb, datastoredb, mainuser, writeuser, readuser):
    template_filename = os.path.join(os.path.dirname(__file__),
                                     u'set_permissions.sql')
    with open(template_filename) as fp:
        template = fp.read()
    return template.format(
        maindb=identifier(maindb),
        datastoredb=identifier(datastoredb),
        mainuser=identifier(mainuser),
        writeuser=identifier(writeuser),
        readuser=identifier(readuser))


@datastore_group.command(
    u'dump',
    help=u'Dump a datastore resource in one of the supported formats.')
@click.argument(u'resource-id', nargs=1)
@click.argument(
    u'output-file',
    type=click.File(u'wb'),
    default=click.get_binary_stream(u'stdout'))
@click.help_option(u'-h', u'--help')
@click_config_option
@click.option(u'--format', default=u'csv', type=click.Choice(DUMP_FORMATS))
@click.option(u'--offset', type=click.IntRange(0, None), default=0)
@click.option(u'--limit', type=click.IntRange(0))
@click.option(u'--bom', is_flag=True)  # FIXME: options based on format
@click.pass_context
def dump(ctx, resource_id, output_file, config, format, offset, limit, bom):
    load_config(config or ctx.obj['config'])

    dump_to(
        resource_id,
        output_file,
        fmt=format,
        offset=offset,
        limit=limit,
        options={u'bom': bom})
