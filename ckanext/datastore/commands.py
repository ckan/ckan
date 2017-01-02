# encoding: utf-8
u"""Perform commands to set up the datastore

Usage:
  paster [options] datastore set-permissions

set-permissions: Emit an SQL script that will set the permissions
for the datastore users as configured in your configuration file.

Options:
  -h --help            This help text
  -c --config=CONFIG   CKAN configuration file
  --plugin=ckan        paster plugin (when used outside of ckan directory)
"""

import os
import sys

from ckan.lib import cli
from ckanext.datastore.helpers import identifier

from docopt import docopt


def datastore_command(command):
    opts = docopt(__doc__)

    cli.load_config(opts['--config'])

    if opts['set-permissions']:
        set_permissions()
    exit(0)  # avoid paster error


# for paster's command index
datastore_command.summary = __doc__.split(u'\n')[0]


def set_permissions():
    write_url = cli.parse_db_config('ckan.datastore.write_url')
    read_url = cli.parse_db_config('ckan.datastore.read_url')
    db_url = cli.parse_db_config('sqlalchemy.url')

    # Basic validation that read and write URLs reference the same database.
    # This obviously doesn't check they're the same database (the hosts/ports
    # could be different), but it's better than nothing, I guess.
    if write_url['db_name'] != read_url['db_name']:
        exit("The datastore write_url and read_url must refer to the same "
             "database!")

    sql = permissions_sql(
        maindb=db_url['db_name'],
        datastoredb=write_url['db_name'],
        mainuser=db_url['db_user'],
        writeuser=write_url['db_user'],
        readuser=read_url['db_user'])

    print(sql)


def permissions_sql(maindb, datastoredb, mainuser, writeuser, readuser):
    template_filename = os.path.join(os.path.dirname(__file__),
                                     'set_permissions.sql')
    with open(template_filename) as fp:
        template = fp.read()
    return template.format(
        maindb=identifier(maindb),
        datastoredb=identifier(datastoredb),
        mainuser=identifier(mainuser),
        writeuser=identifier(writeuser),
        readuser=identifier(readuser))
