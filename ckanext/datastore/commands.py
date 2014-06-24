from __future__ import print_function
import argparse
import os
import sys

import ckan.lib.cli as cli


def _abort(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def _set_permissions(args):
    write_url = cli.parse_db_config('ckan.datastore.write_url')
    read_url = cli.parse_db_config('ckan.datastore.read_url')
    db_url = cli.parse_db_config('sqlalchemy.url')

    # Basic validation that read and write URLs reference the same database.
    # This obviously doesn't check they're the same database (the hosts/ports
    # could be different), but it's better than nothing, I guess.
    if write_url['db_name'] != read_url['db_name']:
        _abort("The datastore write_url and read_url must refer to the same "
               "database!")

    context = {
        'maindb': db_url['db_name'],
        'datastoredb': write_url['db_name'],
        'mainuser': db_url['db_user'],
        'writeuser': write_url['db_user'],
        'readuser': read_url['db_user'],
    }

    sql = _permissions_sql(context)

    print(sql)


def _permissions_sql(context):
    template_filename = os.path.join(os.path.dirname(__file__),
                                     'set_permissions.sql')
    with open(template_filename) as fp:
        template = fp.read()
    return template.format(**context)


parser = argparse.ArgumentParser(
    prog='paster datastore',
    description='Perform commands to set up the datastore',
    epilog='Make sure that the datastore URLs are set properly before you run '
           'these commands!')
subparsers = parser.add_subparsers(title='commands')

parser_set_perms = subparsers.add_parser(
    'set-permissions',
    description='Set the permissions on the datastore.',
    help='This command will help ensure that the permissions for the '
         'datastore users as configured in your configuration file are '
         'correct at the database. It will emit an SQL script that '
         'you can use to set these permissions.',
    epilog='"The ships hung in the sky in much the same way that bricks '
           'don\'t."')
parser_set_perms.set_defaults(func=_set_permissions)


class SetupDatastoreCommand(cli.CkanCommand):
    summary = parser.description

    def command(self):
        self._load_config()

        args = parser.parse_args(self.args)
        args.func(args)
