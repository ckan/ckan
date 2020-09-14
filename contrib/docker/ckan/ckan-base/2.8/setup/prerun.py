import os
import sys
import subprocess
import psycopg2
import urllib2
import time
import re

ckan_ini = os.environ.get('CKAN_INI', '/srv/app/production.ini')

RETRY = 5

def update_plugins():

    plugins = os.environ.get('CKAN__PLUGINS', '')
    print('[prerun] Setting the following plugins in {}:'.format(ckan_ini))
    print(plugins)
    cmd = ['paster', '--plugin=ckan', 'config-tool',
           ckan_ini, 'ckan.plugins = {}'.format(plugins)]
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    print '[prerun] Plugins set.'

    
def check_main_db_connection(retry=None):

    conn_str = os.environ.get('CKAN_SQLALCHEMY_URL')
    if not conn_str:
        print '[prerun] CKAN_SQLALCHEMY_URL not defined, not checking db'
    return check_db_connection(conn_str, retry)


def check_datastore_db_connection(retry=None):

    conn_str = os.environ.get('CKAN_DATASTORE_WRITE_URL')
    if not conn_str:
        print '[prerun] CKAN_DATASTORE_WRITE_URL not defined, not checking db'
    return check_db_connection(conn_str, retry)


def check_db_connection(conn_str, retry=None):

    if retry is None:
        retry = RETRY
    elif retry == 0:
        print '[prerun] Giving up after 5 tries...'
        sys.exit(1)

    try:
        connection = psycopg2.connect(conn_str)

    except psycopg2.Error as e:
        print str(e)
        print '[prerun] Unable to connect to the database, waiting...'
        time.sleep(10)
        check_db_connection(conn_str, retry=retry - 1)
    else:
        connection.close()

        
def check_solr_connection(retry=None):

    if retry is None:
        retry = RETRY
    elif retry == 0:
        print '[prerun] Giving up after 5 tries...'
        sys.exit(1)

    url = os.environ.get('CKAN_SOLR_URL', '')
    search_url = '{url}/select/?q=*&wt=json'.format(url=url)

    try:
        connection = urllib2.urlopen(search_url)
    except urllib2.URLError as e:
        print str(e)
        print '[prerun] Unable to connect to solr, waiting...'
        time.sleep(10)
        check_solr_connection(retry=retry - 1)
    else:
        eval(connection.read())


def init_db():

    db_command = ['paster', '--plugin=ckan', 'db',
                  'init', '-c', ckan_ini]
    print '[prerun] Initializing or upgrading db - start'
    try:
        subprocess.check_output(db_command, stderr=subprocess.STDOUT)
        print '[prerun] Initializing or upgrading db - end'
    except subprocess.CalledProcessError, e:
        if 'OperationalError' in e.output:
            print e.output
            print '[prerun] Database not ready, waiting a bit before exit...'
            time.sleep(5)
            sys.exit(1)
        else:
            print e.output
            raise e


def init_datastore_db():

    conn_str = os.environ.get('CKAN_DATASTORE_WRITE_URL')
    if not conn_str:
        print '[prerun] Skipping datastore initialization'
        return

    datastore_perms_command = ['paster', '--plugin=ckan', 'datastore',
                               'set-permissions', '-c', ckan_ini]

    connection = psycopg2.connect(conn_str)
    cursor = connection.cursor()

    print '[prerun] Initializing datastore db - start'
    try:
        datastore_perms = subprocess.Popen(
            datastore_perms_command,
            stdout=subprocess.PIPE)

        perms_sql = datastore_perms.stdout.read()
        # Remove internal pg command as psycopg2 does not like it
        perms_sql = re.sub('\\\\connect \"(.*)\"', '', perms_sql)
        cursor.execute(perms_sql)
        for notice in connection.notices:
            print notice

        connection.commit()

        print '[prerun] Initializing datastore db - end'
        print datastore_perms.stdout.read()
    except psycopg2.Error as e:
        print '[prerun] Could not initialize datastore'
        print str(e)

    except subprocess.CalledProcessError, e:
        if 'OperationalError' in e.output:
            print e.output
            print '[prerun] Database not ready, waiting a bit before exit...'
            time.sleep(5)
            sys.exit(1)
        else:
            print e.output
            raise e
    finally:
        cursor.close()
        connection.close()


def create_sysadmin():

    name = os.environ.get('CKAN_SYSADMIN_NAME')
    password = os.environ.get('CKAN_SYSADMIN_PASSWORD')
    email = os.environ.get('CKAN_SYSADMIN_EMAIL')

    if name and password and email:

        # Check if user exists
        command = ['paster', '--plugin=ckan', 'user', name, '-c', ckan_ini]

        out = subprocess.check_output(command)
        if 'User:None' not in re.sub(r'\s', '', out):
            print '[prerun] Sysadmin user exists, skipping creation'
            return

        # Create user
        command = ['paster', '--plugin=ckan', 'user', 'add',
                   name,
                   'password=' + password,
                   'email=' + email,
                   '-c', ckan_ini]

        subprocess.call(command)
        print '[prerun] Created user {0}'.format(name)

        # Make it sysadmin
        command = ['paster', '--plugin=ckan', 'sysadmin', 'add',
                   name,
                   '-c', ckan_ini]

        subprocess.call(command)
        print '[prerun] Made user {0} a sysadmin'.format(name)


if __name__ == '__main__':

    maintenance = os.environ.get('MAINTENANCE_MODE', '').lower() == 'true'

    if maintenance:
        print '[prerun] Maintenance mode, skipping setup...'
    else:
        check_main_db_connection()
        init_db()
        update_plugins()
        check_datastore_db_connection()
        init_datastore_db()
        check_solr_connection()
        create_sysadmin()