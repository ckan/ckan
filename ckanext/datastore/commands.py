from __future__ import print_function
import argparse
import getpass
import os
import sys

import pylons
import sqlalchemy

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

    if args.execute:
        if args.use_config_credentials:
            url = pylons.config['sqlalchemy.url']
        else:
            url = ['postgresql://', args.username]
            # This awkward double-negative is because --no-password is the name
            # of the parameter to psql, and it's kind to be consistent.
            if not args.no_password:
                password = getpass.getpass("Password for user {user}: ".format(
                    user=args.username))
                url.append(':{0}'.format(password))
            url.append('@{0}'.format(args.host))
            if args.port:
                url.append(':{0}'.format(args.port))

            url = "".join(url)

        _set_permissions_execute(url, sql)
    else:
        print(sql)


def _permissions_sql(context):
    template_filename = os.path.join(os.path.dirname(__file__),
                                     'set_permissions.sql')
    with open(template_filename) as fp:
        template = fp.read()

    return template.format(**context)


def _set_permissions_execute(url, sql):
    engine = sqlalchemy.create_engine(url)
    conn = engine.connect()
    conn.execute('commit')
    conn.execute(sql)


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
         'correct at the database. By default it will emit an SQL script that '
         'you can use to set these permissions. You can also request that it '
         'execute the script by connecting to the database directly.',
    epilog='"The ships hung in the sky in much the same way that bricks '
           'don\'t."',
    add_help=False)
# Re-add --help without -h so that we can provide the same args as psql.
parser_set_perms.add_argument('--help', action='help',
                              help='show this help message and exit')
parser_set_perms.add_argument('-x', '--execute', action='store_true',
                              help='connect to the database to set the '
                                   'permissions')
parser_set_perms.add_argument('--use-config-credentials',
                              action='store_true',
                              help='use db credentials from config file')
parser_set_perms.add_argument('-h', '--host', help='db server host')
parser_set_perms.add_argument('-p', '--port', type=int, help='db server port')
parser_set_perms.add_argument('-U', '--username', help='db superuser username')
parser_set_perms.add_argument('-w', '--no-password', action='store_true',
                              help='never prompt for password')
parser_set_perms.set_defaults(func=_set_permissions,
                              host='localhost',
                              port=5432,
                              username=getpass.getuser())


class SetupDatastoreCommand(cli.CkanCommand):
    summary = parser.description

    def command(self):
        self._load_config()

        args = parser.parse_args(self.args)
        args.func(args)
