'''
Setup the right permissions on the datastore db
'''

import sys
import os
import logging


def _run_cmd(command_line, inputstring=''):
    logging.info("Running:", command_line)
    import subprocess
    p = subprocess.Popen(
        command_line, shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout_value, stderr_value = p.communicate(input=inputstring)
    if stderr_value or p.returncode:
        print '\nAn error occured: {0}'.format(stderr_value)
        sys.exit(1)


def _run_sql(sql, as_sql_user, database='postgres'):
    logging.debug("Executing: \n#####\n", sql, "\n####\nOn database:", database)
    _run_cmd("sudo -u '{username}' psql --dbname='{database}' --no-password --set ON_ERROR_STOP=1".format(
        username=as_sql_user,
        database=database
    ), inputstring=sql)


def set_permissions(pguser, ckandb, datastoredb, ckanuser, writeuser, readonlyuser):
    __dir__ = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(__dir__, 'set_permissions.sql')
    with open(filepath) as f:
        set_permissions_sql = f.read()

        sql = set_permissions_sql.format(
            ckandb=ckandb,
            datastoredb=datastoredb,
            ckanuser=ckanuser,
            writeuser=writeuser,
            readonlyuser=readonlyuser)

        _run_sql(sql,
                  as_sql_user=pguser,
                  database=datastoredb)


if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(
        description='Set the permissions on the CKAN datastore. ',
        epilog='"The ships hung in the sky in much the same way that bricks don\'t."')

    argparser.add_argument('-p', '--pg_super_user', dest='pguser', default='postgres', type=str,
                       help="the postgres super user")

    argparser.add_argument(dest='ckandb', default='ckan', type=str,
                       help="the name of the ckan database")
    argparser.add_argument(dest='datastoredb', default='datastore', type=str,
                       help="the name of the datastore database")
    argparser.add_argument(dest='ckanuser', default='ckanuser', type=str,
                       help="username of the ckan postgres user")
    argparser.add_argument(dest='writeuser', default='writeuser', type=str,
                       help="username of the datastore user that can write")
    argparser.add_argument(dest='readonlyuser', default='readonlyuser',
                       help="username of the datastore user who has only read permissions")

    args = argparser.parse_args()

    set_permissions(
        pguser=args.pguser,
        ckandb=args.ckandb,
        datastoredb=args.datastoredb,
        ckanuser=args.ckanuser,
        writeuser=args.writeuser,
        readonlyuser=args.readonlyuser
    )
