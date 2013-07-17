'''
CKAN Fabric
===========

Purpose: to automate CKAN deployment, backup and other maintenance operations

Usage: fab {config} {command}

{config}:
This parameter describes the configuration of the server where the CKAN
instance is, including the host name, ssh user, pathnames, code revision, etc.
  config_0:{host_name} - the default: ssh to okfn@{host_name},
                         ckan is in ~/var/srvc/{host_name} and uses
                         code from the metastable revision.
  config_dev_hmg_ckan_net - a custom setup for dev-hmg.ckan.net because
                         this instance uses code revision 'default'.
  config_local:{base_dir},{instance_name} - for local operations. Host is
                         'localhost' (it still has to ssh in, so requires
                         password) and you must specify:
                         * {base_dir} - path to ckan instances
                         * {instance_name} - folder name for the specific
                                             ckan instance you want
  config_local_dev:{base_dir},{instance_name} - for local operations, but
                         for developers that have their CKAN repo separate
                         from their virtual environment. It assumes you have:
                         * {base_dir}/{instance_name} - ckan code repo
                         * {base_dir}/pyenv-{instance_name} - virtual env

{command}:
This parameter describes the operation you want to do on the CKAN instance
specified in {config}. For example you can start with 'deploy' with host and
database parameters to deploy the CKAN code, initialise the database and
configure it to work. (There are then a couple of extra manual steps to
complete the deployment - see doc/deployment.rst). Once there are some
packages on there you can do a 'backup' of the db and later 'restore' the file.
You can check the 'logs' for latest errors, switch to another 'apache_config'
such as for a maintenance mode, check the version of the code running using
'status'. When the code is updated you can load it on using 'deploy' (usually
without specifying any parameters) then 'restart_apache'.

For a list of all parameters from {config} & {command} do: fab -l

Examples:
=========

Deploy a new CKAN instance called new.ckan.net on new.ckan.net::

    # see fab -d config_0 for more info
    fab config_0:new.ckan.net,db_pass={your-db-pass} deploy

Note, a database is created with this password if it does not already exist.

Deploy new.ckan.net but the DNS is not setup yet::

    fab config_0:new.ckan.net,hosts_str=132.23.4.15,db_pass={your-db-pass} deploy

Deploy to a local directory::

    fab config_local:~/test,test deploy

'''
from __future__ import with_statement
import os
import sys
import datetime
import urllib2
import subprocess

from fabric.api import *
from fabric.contrib.console import *
from fabric.contrib.files import *

# defaults
env.ckan_instance_name = 'test' # e.g. test.ckan.net
env.base_dir = os.getcwd() # e.g. /home/jsmith/var/srvc
env.local_backup_dir = os.path.expanduser('~/db_backup')
env.ckan_repo = 'https://github.com/okfn/ckan/raw/%s/'
pip_requirements = 'requirements.txt'
env.skip_setup_db = False

def config_local(base_dir, ckan_instance_name, db_user=None, db_host=None,
                 db_pass=None, 
                 skip_setup_db=None, no_sudo=None, revision=None):
    '''Run on localhost. e.g. config_local:~/test,myhost.com
                            puts it at ~/test/myhost.com
                            '''
    env.hosts = ['localhost']
    env.ckan_instance_name = ckan_instance_name # e.g. 'test.ckan.net'
    env.base_dir = os.path.expanduser(base_dir)    # e.g. ~/var/srvc
    if db_user:
        env.db_user = db_user
    if db_pass:
        env.db_pass = db_pass
    if db_host:
        env.db_host = db_host
    if skip_setup_db != None:
        env.skip_setup_db = skip_setup_db    
    if no_sudo != None:
        env.no_sudo = no_sudo
    env.revision = revision if revision else 'metastable'
        

def config_local_dev(base_dir, ckan_instance_name):
    config_local(base_dir, ckan_instance_name)
    env.config_ini_filename = 'development.ini'
    env.pyenv_dir = os.path.join(base_dir, 'pyenv-%s' % ckan_instance_name)
    env.serve_url = 'localhost:5000'

def config_staging_hmg_ckan_net():
    env.user = 'okfn'
    env.base_dir = '/home/%s' % env.user
    env.ckan_instance_name = 'staging-hmg.ckan.net'
    env.revision = 'stable'

def config_test_hmg_ckan_net():
    name = 'test-hmg.ckan.net'
    config_0(name, hosts_str=name, revision='stable')

def config_hmg_ckan_net_1():
    env.user = 'ckan1'
    env.base_dir = '/home/%s' % env.user
    env.cmd_pyenv = os.path.join(env.base_dir, 'ourenv')
    env.no_sudo = None
    env.ckan_instance_name = 'hmg.ckan.net'
    env.apache_config = 'hmg.ckan.net'
    env.hosts = ['ssh.hmg.ckan.net']
    env.wsgi_script_filepath = None # os.path.join(env.base_dir, 'hmg.ckan.net/pyenv/bin/pylonsapp_modwsgi.py')
    env.revision = 'stable'

def config_hmg_ckan_net_2():
    config_hmg_ckan_net_1()
    env.ckan_instance_name = 'hmg.ckan.net.2'
    env.hosts = ['ssh.hmg.ckan.net']
    env.config_ini_filename = 'hmg.ckan.net.ini'

def config_hmg2_ckan_net_1(db_pass=None):
    env.user = 'okfn'
    env.hosts = ['hmg2.ckan.net']
    env.base_dir = '/home/%s/var/srvc' % env.user
#    env.wsgi_script_filepath = os.path.join(env.base_dir, 'pylonsapp_modwsgi.py')
    env.revision = 'default'
    env.db_pass = db_pass
    env.ckan_instance_name = 'hmg2.ckan.net.1'
    env.config_ini_filename = 'hmg2.ckan.net.ini'
    env.log_filename_pattern = 'hmg2.ckan.net.%s.log'

def config_hmg2_ckan_net_2(db_pass=None):
    config_hmg2_ckan_net_1(db_pass)
    env.ckan_instance_name = 'hmg2.ckan.net.2'

def config_hmg2_ckan_net():
    # i.e. whichever instance is current
    config_hmg2_ckan_net_1()
    env.ckan_instance_name = 'hmg2.ckan.net.current'
    env.switch_between_ckan_instances = ['hmg2.ckan.net.1', 'hmg2.ckan.net.2']

def config_test_ckan_net():
    config_0('test.ckan.net', revision='default')

def config_dev_hmg_ckan_net():
    config_0('dev-hmg.ckan.net', revision='default',
             user='okfn')

def config_0(name,
             hosts_str='',
             revision='metastable',
             db_user=None,
             db_pass='',
             db_host='localhost',
             user='okfn'
        ):
    '''Configurable configuration: fab -d gives full info.
    
    @param name: name of instance (e.g. xx.ckan.net)
    @param hosts_str: hosts to run on (--host does not work correctly).
        Defaults to name if not supplied.
    @param revision: branch/tag/revision to find pip requirements in the ckan
        repo. (default is 'metastable')
    @param db_user: db user name (assumes it is already created). Defaults to
                    value of 'user'.
    @param db_pass: password to use when setting up db user (if needed)
    @param db_host: db host to use when setting up db (if needed)
    @param user: user to log into host as, if not current user
    '''
    env.user = user or os.environ['USER']
    if hosts_str:
        env.hosts = hosts_str.split()
    if not hosts_str and not env.hosts:
        env.hosts = [name]
    env.ckan_instance_name = name
    env.config_ini_filename = '%s.ini' % name
    # check if the host is just a squid caching a ckan running on another host
    assert len(env.hosts) == 1, 'Must specify one host'
    env.host_string = env.hosts[0]
    if exists('/etc/squid3/squid.conf'):
        # e.g. acl eu7_sites dstdomain ckan.net
        conf_line = run('grep -E "^acl .* %s" /etc/squid3/squid.conf' % env.host_string)
        if conf_line:
            host_txt = conf_line.split()[1].replace('_sites', '.okfn.org')
            env.hosts = [host_txt]
            print 'Found Squid cache is of CKAN host: %s' % host_txt
            env.user = 'okfn'
        else:
            print 'Found Squid cache but did not find host in config.'
    env.base_dir = '/home/%s/var/srvc' % env.user
    env.revision = revision
    env.db_user = db_user or env.user
    env.db_pass = db_pass
    env.db_host = db_host
    env.log_filename_pattern = name + '.%s.log'
    
def _setup():
    def _default(key, value):
        if not hasattr(env, key):
            setattr(env, key, value)
    _default('config_ini_filename', '%s.ini' % env.ckan_instance_name)
    _default('instance_path', os.path.join(env.base_dir,
        env.ckan_instance_name))
    if hasattr(env, 'local_backup_dir'):
        env.local_backup_dir = os.path.expanduser(env.local_backup_dir)
    _default('pyenv_dir', os.path.join(env.instance_path, 'pyenv'))
    _default('serve_url', env.ckan_instance_name)
    _default('wsgi_script_filepath', os.path.join(env.pyenv_dir, 'bin', '%s.py'
        % env.ckan_instance_name))
    _default('who_ini_filepath', os.path.join(env.pyenv_dir, 'src', 'ckan',
        'who.ini'))
    _default('db_user', env.user)
    _default('db_host', 'localhost')
    _default('db_name', env.ckan_instance_name)
    _default('pip_from_pyenv', None)
    _default('apache_sites_available', '/etc/apache2/sites-available/')
    _default('apache_sites_enabled', '/etc/apache2/sites-enabled/')
    _default('apache_config', env.ckan_instance_name)

def deploy():
    '''Deploy app on server. Keeps existing config files.'''
    assert env.ckan_instance_name
    assert env.base_dir
    _setup()
    _mkdir(env.instance_path)
    pip_req = env.ckan_repo % env.revision + pip_requirements
    with cd(env.instance_path):

        # get latest requirements.txt
        print 'Getting requirements from revision: %s' % env.revision
        latest_pip_file = urllib2.urlopen(pip_req)
        tmp_pip_requirements_filepath = os.path.join('/tmp', pip_requirements)
        local_pip_file = open(tmp_pip_requirements_filepath, 'w')
        local_pip_file.write(latest_pip_file.read())
        local_pip_file.close()
        remote_pip_filepath = os.path.join(env.instance_path, pip_requirements)
        put(tmp_pip_requirements_filepath, remote_pip_filepath)
        assert exists(remote_pip_filepath)

        # create python environment
        if not exists(env.pyenv_dir):
            _run_in_cmd_pyenv('virtualenv %s' % env.pyenv_dir)
        else:
            print 'Virtualenv already exists: %s' % env.pyenv_dir

        # Run pip
        print 'Pip download cache: %r' % os.environ.get('PIP_DOWNLOAD_CACHE')
        _pip_cmd('pip -E %s install -r %s' % (env.pyenv_dir, pip_requirements))

        # create config ini file
        if not exists(env.config_ini_filename):
            # paster make-config doesn't overwrite if ini already exists
            _run_in_pyenv('paster make-config --no-interactive ckan %s' % env.config_ini_filename)
            dburi = '^sqlalchemy.url.*'
            # e.g. 'postgres://tester:pass@localhost/ckantest3'
            newdburi = 'sqlalchemy.url = postgres://%s:%s@%s/%s' % (
                    env.db_user, env.db_pass, env.db_host, env.db_name)
            # sed does not find the path if not absolute (!)
            config_path = os.path.join(env.instance_path, env.config_ini_filename)
            sed(config_path, dburi, newdburi, backup='')
            site_id = '^.*ckan.site_id.*'
            new_site_id = 'ckan.site_id = %s' % env.ckan_instance_name
            sed(config_path, site_id, new_site_id, backup='')
            if not env.skip_setup_db:
                setup_db()
            _run_in_pyenv('paster --plugin ckan db init --config %s' % env.config_ini_filename)
        else:
            print 'Config file already exists: %s/%s' % (env.instance_path, env.config_ini_filename)
            _run_in_pyenv('paster --plugin ckan db upgrade --config %s' % env.config_ini_filename)

        # create wsgi script
        if env.wsgi_script_filepath:
            if not exists(env.wsgi_script_filepath):
                print 'Creating WSGI script: %s' % env.wsgi_script_filepath
                context = {'instance_dir':env.instance_path,
                           'config_file':env.config_ini_filename,
                           } #e.g. pyenv_dir='/home/ckan1/hmg.ckan.net'
                             #     config_file = 'hmg.ckan.net.ini'
                _create_file_by_template(env.wsgi_script_filepath, wsgi_script, context)
                run('chmod +r %s' % env.wsgi_script_filepath)
            else:
                print 'WSGI script already exists: %s' % env.wsgi_script_filepath
        else:
            print 'Leaving WSGI script alone'

        # create link to who.ini
        assert exists(env.who_ini_filepath)
        whoini_dest = os.path.join(env.instance_path, 'who.ini')
        if not exists(whoini_dest):
            run('ln -f -s %s %s' % (env.who_ini_filepath, whoini_dest))
        else:
            print 'Link to who.ini already exists'

        # create pylons cache directory
        _create_live_data_dir('Pylons cache', _get_pylons_cache_dir())
        _create_live_data_dir('OpenID store', _get_open_id_store_dir())

    print 'For details of remaining setup, see deployment.rst.'

def setup_db(db_details=None):
    '''Create a DB (if one does not already exist).

        * Requires sudo access.
        * Also creates db user if relevant user does not exist.

    @param db_details: dictionary with values like db_user, db_name. If not
        provided load from existing pylons config using _get_db_config()
    '''
    if not db_details:
        db_details = _get_db_config()
    dbname = db_details['db_name']
    if db_details['db_host'] != 'localhost':
        raise Exception('Cannot setup db on non-local host (sudo will not work!)')
    output = sudo('psql -l', user='postgres')
    if ' %s ' % dbname in output:
        print 'DB already exists with name: %s' % dbname
        return 0
    users = sudo('psql -c "\du"', user='postgres')
    dbuser = db_details['db_user']
    if not dbuser in users:
        createuser = '''psql -c "CREATE USER %s WITH PASSWORD '%s';"''' % (dbuser, db_details['db_pass'])
        sudo(createuser, user='postgres')
    else:
        print('User %s already exists' % dbuser)
    sudo('createdb --owner %s %s' % (dbuser, dbname), user='postgres')

def restart_apache():
    'Restart apache'
    sudo('/etc/init.d/apache2 restart')

def reload_apache():
    'Reload apache config'
    sudo('/etc/init.d/apache2 reload')

def status():
    'Provides version number info'
    _setup()
    with cd(env.instance_path):
        _run_in_cmd_pyenv('pip freeze')
        run('cat %s' % env.config_ini_filename)
    with cd(os.path.join(env.pyenv_dir, 'src', 'ckan')):
        run('git log -n1')
        run('git name-rev --name-only HEAD')
        run('grep version ckan/__init__.py')

def apache_config(set_config=None):
    '''View and change the currently enabled apache config for this site'''
    _setup()
    enabled_config = get_enabled_apache_config()
    available_configs = get_available_apache_configs()
    print 'Available modes: %s' % available_configs

    if set_config == None:
        print 'Current mode: %s' % enabled_config
    else:
        assert set_config in available_configs
        if enabled_config:
            sudo('a2dissite %s' % enabled_config)
        sudo('a2ensite %s' % set_config)
        reload_apache()

def get_available_apache_configs():
    available_configs = run('ls %s' % env.apache_sites_available).split('\n')
    related_available_configs = [fname for fname in available_configs if env.apache_config in fname]
    assert related_available_configs, \
           'No recognised available apache config in: %r' % available_configs
    return related_available_configs

def get_enabled_apache_config():
    with cd(env.apache_sites_enabled):
        related_enabled_configs = run('ls %s*' % (env.apache_config)).split('\n')
    assert len(related_enabled_configs) <= 1, \
           'Seemingly more than one apache config enabled for this site: %r' %\
           related_enabled_configs
    return related_enabled_configs[0] if related_enabled_configs else None


def backup():
    'Backup database'
    _setup()
    if hasattr(env, 'backup_dir'):
        backup_dir = env.backup_dir
    else:
        backup_dir = os.path.join(env.base_dir, 'backup')
    _mkdir(backup_dir)
    pg_dump_filepath = _get_unique_filepath(backup_dir, exists, 'pg_dump')

    with cd(env.instance_path):
        assert exists(env.config_ini_filename), "Can't find config file: %s/%s" % (env.instance_path, env.config_ini_filename)
    db_details = _get_db_config()
    assert db_details['db_type'] in ('postgres', 'postgresql')
    port_option = '-p %s' % db_details['db_port'] if db_details['db_port'] else ''
    run('export PGPASSWORD=%s&&pg_dump -U %s -h %s %s %s > %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_host'], port_option, db_details['db_name'], pg_dump_filepath), shell=False)
    assert exists(pg_dump_filepath)
    run('ls -l %s' % pg_dump_filepath)
    # copy backup locally
    if env.host_string != 'localhost':
        # zip it up
        pg_dump_filename = os.path.basename(pg_dump_filepath)
        zipped_pg_dump_filepath = os.path.join('/tmp', pg_dump_filename) + '.gz'
        run('gzip -c %s > %s' % (pg_dump_filepath, zipped_pg_dump_filepath))
        # do the copy
        local_backup_dir = os.path.join(env.local_backup_dir, env.host_string)
        if not os.path.exists(local_backup_dir):
            os.makedirs(local_backup_dir)
        local_zip_filepath = os.path.join(local_backup_dir, pg_dump_filename) + '.gz'
        get(zipped_pg_dump_filepath, local_zip_filepath)
        # unzip it
        subprocess.check_call('gunzip %s' % local_zip_filepath, shell=True)
        local_filepath = os.path.join(local_backup_dir, pg_dump_filename)
        print 'Backup saved locally: %s' % local_filepath

def restore_from_local(pg_dump_filepath):
    '''Like restore but from a local pg dump'''
    pg_dump_filepath = os.path.expanduser(pg_dump_filepath)
    assert os.path.exists(pg_dump_filepath)
    pg_dump_filename = os.path.basename(pg_dump_filepath)
    if not pg_dump_filename.endswith('.gz'):
        new_pg_dump_filepath = os.path.join('/tmp', pg_dump_filename) + '.gz'
        subprocess.check_call('gzip -c %s > %s' % (pg_dump_filepath, new_pg_dump_filepath), shell=True)
        pg_dump_filepath = new_pg_dump_filepath
    remote_filepath = os.path.join('/tmp', pg_dump_filename) + '.gz'
    put(pg_dump_filepath, remote_filepath)
    run('gunzip %s' % remote_filepath)
    remote_filepath = remote_filepath.rstrip('.gz')
    restore(remote_filepath)

def restore(pg_dump_filepath):
    '''Restore ckan from an existing dump'''
    _setup()
    pg_dump_filepath = os.path.expanduser(pg_dump_filepath)
    assert exists(pg_dump_filepath), 'Cannot find file: %s' % pg_dump_filepath
    db_details = _get_db_config()
    confirm('Are you sure you want to overwrite database for %s %s?' % \
            (env.host_string, env.ckan_instance_name),
            default=False)
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan db clean --config %s' % env.config_ini_filename)
    assert db_details['db_type'] in ('postgres', 'postgresql')
    port_option = '-p %s'  % db_details['db_port'] if db_details['db_port'] else ''
    run('export PGPASSWORD=%s&&psql -U %s -d %s -h %s %s -f %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_name'], db_details['db_host'], port_option, pg_dump_filepath), shell=False)
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan db upgrade --config %s' % env.config_ini_filename)
        _run_in_pyenv('paster --plugin ckan db init --config %s' % env.config_ini_filename)

def load_from_local(format, csv_filepath):
    '''Like load but with a local file'''
    csv_filepath = os.path.expanduser(csv_filepath)
    assert os.path.exists(csv_filepath)
    csv_filename = os.path.basename(csv_filepath)
    remote_filepath = os.path.join('/tmp', csv_filename)
    put(csv_filepath, remote_filepath)
    load(format, remote_filepath)

def load(format, csv_filepath):
    '''Run paster db load with supplied material'''
    assert format in ('cospread', 'data4nr')
    _setup()
    csv_filepath = os.path.expanduser(csv_filepath)
    assert exists(csv_filepath), 'Cannot find file: %s' % csv_filepath
    db_details = _get_db_config()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan db load-%s %s --config %s' % (format, csv_filepath, env.config_ini_filename))
    
def test():
    '''Run paster test-data'''
    _setup()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan test-data %s --config %s' % (env.serve_url, env.config_ini_filename))

def upload_i18n(lang):
    _setup()
    localpath = 'ckan/i18n/%s/LC_MESSAGES/ckan.mo' % lang
    remotepath = os.path.join(env.pyenv_dir, 'src', 'ckan', localpath)
    assert exists(env.pyenv_dir)
    remotedir = os.path.dirname(remotepath)
    _mkdir(remotedir)
    put(localpath, remotepath)
    current_lang = _get_ini_value('lang')
    if current_lang != lang:
        print "Warning: current language set to '%s' not '%s'." % (current_lang, lang)

def paster(cmd):
    '''Run specified paster command'''
    _setup()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan %s --config %s' % (cmd, env.config_ini_filename))

def sysadmin_list():
    '''Lists sysadmins'''
    _setup()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan sysadmin list --config %s' % env.config_ini_filename)

def sysadmin_create(open_id):
    '''Creates sysadmins with the given OpenID'''
    _setup()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan sysadmin create %s --config %s' % (open_id, env.config_ini_filename))

def switch_instance():
    '''For multiple instance servers, switches the one that is active.'''
    _setup()
    current_instance = _get_current_instance()
    # check existing symbolic link
    with cd(env.base_dir):
        if current_instance:
            next_instance_index = (env.switch_between_ckan_instances.index(current_instance) + 1) % len(env.switch_between_ckan_instances)
            # delete existing symbolic link
            run('rm %s' % env.ckan_instance_name)
        else:
            next_instance_index = 0
        next_instance = env.switch_between_ckan_instances[next_instance_index]
        run('ln -s %s %s' % (next_instance, env.ckan_instance_name))
    # restart apache
    restart_apache()
    print 'Current instance changed %s -> %s' % (current_instance, next_instance)

def apache_log(cmd='tail', log='error'):
    '''Displays the apache log.
    @log - error or custom'''
    #todo make this more flexible
    filename = env.log_filename_pattern % log
    run_func = run if hasattr(env, 'no_sudo') else sudo
    run_func('%s /var/log/apache2/%s' % (cmd, filename))

def log(cmd='tail'):
    '''Displays the ckan log.'''
    filepath = _get_ckan_log_filename()
    run('%s %s' % (cmd, filepath))

def current():
    '''Tells you which instance is current for switchable instances'''
    assert env.switch_between_ckan_instances
    current_instance = _get_current_instance()
    print 'Current instance is: %s' % current_instance
    if len(env.switch_between_ckan_instances) == 2:
        current_instance_index = env.switch_between_ckan_instances.index(current_instance)
        reserve_instance_index = (current_instance_index + 1) % 2
        env.ckan_instance_name = env.switch_between_ckan_instances[reserve_instance_index]
        print 'Reserve instance is: %s' % env.ckan_instance_name


## ===================================
#  Helper Methods

def _mkdir(dir):
    if not exists(dir):
        run('mkdir -p %s' % dir)
    else:
        print 'Path already exists: %s' % dir
    
def _get_unique_filepath(dir, exists_func, extension):
    def get_filepath(dir, suffix):
        date = datetime.datetime.today().strftime('%Y-%m-%d')
        if suffix:
            return os.path.join(dir, '%s.%s.%s.%s' % (env.ckan_instance_name, date, suffix, extension))
        else:
            return os.path.join(dir, '%s.%s.%s' % (env.ckan_instance_name, date, extension))
    count = 0
    while count == 0 or exists_func(filepath):
        filepath = get_filepath(dir, count)
        count += 1
        assert count < 100, 'Unique filename (%s) overflow in dir: %s' % (extension, dir)
    return filepath

def _get_ini_value(key, ini_filepath=None):
    if not ini_filepath:
        # default to config ini
        ini_filepath = os.path.join(env.instance_path, env.config_ini_filename)
    assert exists(ini_filepath), 'Could not find CKAN instance config at: ' % ini_filepath
    with settings(warn_only=True):
        output = run('grep -E "^%s" %s' % (key, ini_filepath))
    if output == '':
        print 'Did not find key "%s" in config.' % key
        return None
    lines = output.split('\n')
    assert len(lines) == 1, 'Difficulty finding key %s in config %s:\n%s' % (key, ini_filepath, output)
    value = re.match('^%s[^=]=\s*(.*)' % key, lines[0]).groups()[0]
    return value

def _get_db_config():
    url = _get_ini_value('sqlalchemy.url')
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)
    if not db_details_match:
        raise Exception('Could not extract db details from url: %r' % url)
    db_details = db_details_match.groupdict()
    return db_details

def _get_ckan_pyenv_dict():
    # we would only have this path for dev installs so disabling ...
    # return {'here':os.path.join(env.pyenv_dir, 'src', 'ckan')}
    return {'here': env.instance_path}

def _get_pylons_cache_dir():
    cache_dir = _get_ini_value('cache_dir')
    # e.g. '%(here)s/data'
    return cache_dir % _get_ckan_pyenv_dict()

def _get_open_id_store_dir():
    store_file_path = _get_ini_value('store_file_path', env.who_ini_filepath)
    # e.g. '%(here)s/sstore'
    return store_file_path % _get_ckan_pyenv_dict()

def _create_live_data_dir(readable_name, dir):
    if not exists(dir):
        print 'Setting up %s directory: %s' % (readable_name, dir)
        run('mkdir -p %s' % dir)
        if hasattr(env, 'no_sudo'):
            # Doesn't need sudo
            run('chmod gu+wx -R %s' % dir)
        else:
            run('chmod g+wx -R %s' % dir)
            sudo('chgrp -R www-data %s' % dir)
    else:
        print '%s directory already exists: %s' % (readable_name, dir)
        
def _get_ckan_log_filename():
    _setup()
    ini_filepath = os.path.join(env.instance_path, env.config_ini_filename)
    assert exists(ini_filepath)
    key = 'args'
    with settings(warn_only=True):
        output = run('grep -E "^%s" %s' % (key, ini_filepath))
    if output == '':
        print 'Did not find key "%s" in config.' % key
        return None
    lines = output.split('\n')
    matching_args = []
    for line in lines:
        match = re.match('^%s\s*=\s*\(["\'](.*?)["\'].*' % key, line)
        if match:
            matching_args.append(match.groups()[0])
    if not matching_args:
        print 'Could not find %r in config to find CKAN log.' % key
        return None
    if len(matching_args) > 1:
        print 'Many matches for %r in config, looking for CKAN log: %r' % (key, matching_args)
        return None
    return matching_args[0]

def _run_in_pyenv(command):
    '''For running commands that are installed the instance\'s python
    environment'''
    activate_path = os.path.join(env.pyenv_dir, 'bin', 'activate')
    run('source %s&&%s' % (activate_path, command))

def _pip_cmd(command):
    '''Looks for pip in the pyenv before finding it in the cmd pyenv'''
    if env.pip_from_pyenv == None:
        env.pip_from_pyenv = bool(exists(os.path.join(env.pyenv_dir, 'bin', 'pip')))
    if env.pip_from_pyenv:
        return _run_in_pyenv(command)
    else:
        return _run_in_cmd_pyenv(command)            
    
def _run_in_cmd_pyenv(command):
    '''For running commands that are installed in a specific python
    environment specified by env.cmd_pyenv'''
    if hasattr(env, 'cmd_pyenv'):
        activate_path = os.path.join(env.cmd_pyenv, 'bin', 'activate')
        command = 'source %s&&%s' % (activate_path, command)
    run(command)

def _create_file_by_template(destination_filepath, template, template_context):
    run('mkdir -p %s' % os.path.dirname(destination_filepath))
    _upload_template_buffer(template, destination_filepath, template_context)

def _upload_template_buffer(template, destination, context=None, use_sudo=False):
    basename = os.path.basename(destination)
    temp_destination = '/tmp/' + basename

    # This temporary file should not be automatically deleted on close, as we
    # need it there to upload it (Windows locks the file for reading while open).
    tempfile_fd, tempfile_name = tempfile.mkstemp()
    output = open(tempfile_name, "w+b")
    # Init
    text = None
    text = template
    if context:
        text = text % context
    output.write(text)
    output.close()

    # Upload the file.
    put(tempfile_name, temp_destination)
    os.close(tempfile_fd)
    os.remove(tempfile_name)

    func = use_sudo and sudo or run
    # Back up any original file (need to do figure out ultimate destination)
    to_backup = destination
    with settings(hide('everything'), warn_only=True):
        # Is destination a directory?
        if func('test -f %s' % to_backup).failed:
            # If so, tack on the filename to get "real" destination
            to_backup = destination + '/' + basename
    if exists(to_backup):
        func("cp %s %s.bak" % (to_backup, to_backup))
    # Actually move uploaded template to destination
    func("mv %s %s" % (temp_destination, destination))

def _get_current_instance():
    '''For switchable instances, returns the current one in use.'''
    if not env.has_key('switch_between_ckan_instances'):
        print 'CKAN instance "%s" is not switchable.' % env.ckan_instance_name
        sys.exit(1)
    with cd(env.base_dir):
        if exists(env.ckan_instance_name):
            current_instance = run('python -c "import os; assert os.path.islink(\'%s\'); print os.path.realpath(\'%s\')"' % (os.path.join(env.base_dir, env.ckan_instance_name), env.ckan_instance_name))
            current_instance = current_instance.replace(env.base_dir + '/', '')
            assert current_instance in env.switch_between_ckan_instances, \
                   'Instance "%s" not in list of switchable instances.' \
                   % current_instance
        else:
            current_instance = None
    return current_instance

wsgi_script = """
import os
instance_dir = '%(instance_dir)s'
config_file = '%(config_file)s'
pyenv_bin_dir = os.path.join(instance_dir, 'pyenv', 'bin')
activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))
from paste.deploy import loadapp
config_filepath = os.path.join(instance_dir, config_file)
application = loadapp('config:%%s' %% config_filepath)
"""
