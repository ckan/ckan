# std usage:
#   fab std_config:{name} [operation] 
#
#   for details of operations do fab -l
#
# Examples:
#   deploy to a local directory: fab local:~/test,test deploy
from __future__ import with_statement
import os
import datetime
import urllib2
import subprocess

from fabric.api import *
from fabric.contrib.console import *
from fabric.contrib.files import *

# defaults
env.ckan_instance_name = 'test' # e.g. test.ckan.net
env.base_dir = os.getcwd() # e.g. /home/jsmith/var/srvc
env.local_backup_dir = '~/db_backup'
env.ckan_repo = 'http://knowledgeforge.net/ckan/hg/raw-file/tip/'
env.pip_requirements = 'pip-requirements.txt'

def config_local(base_dir, ckan_instance_name):
    '''Run on localhost. e.g. local:~/test,myhost.com
                            puts it at ~/test/myhost.com
                            '''
    env.hosts = ['localhost']
    env.ckan_instance_name = ckan_instance_name # e.g. 'test.ckan.net'
    env.base_dir = os.path.expanduser(base_dir)    # e.g. ~/var/srvc

def config_local_dev(base_dir, ckan_instance_name):
    local(base_dir, ckan_instance_name)
    env.config_ini_filename = 'development.ini'
    env.pyenv_dir = os.path.join(base_dir, 'pyenv-%s' % ckan_instance_name)
    env.serve_url = 'localhost:5000'

def config_staging_hmg_ckan_net():
    env.user = 'ckan1'
    env.base_dir = '/home/%s' % env.user
    env.cmd_pyenv = os.path.join(env.base_dir, 'ourenv')
    env.ckan_instance_name = 'staging.hmg.ckan.net'
    env.pip_requirements = 'pip-requirements-stable.txt'

def config_test_hmg_ckan_net():
    staging_hmg_ckan_net()
    env.ckan_instance_name = 'test.hmg.ckan.net'
    env.hosts = ['ssh.' + env.ckan_instance_name]

def config_hmg_ckan_net_1():
    env.user = 'ckan1'
    env.base_dir = '/home/%s' % env.user
    env.cmd_pyenv = os.path.join(env.base_dir, 'ourenv')
    env.no_sudo = None
    env.ckan_instance_name = 'hmg.ckan.net'
    env.hosts = ['ssh.hmg.ckan.net']
    env.wsgi_script_filepath = None # os.path.join(env.base_dir, 'hmg.ckan.net/pyenv/bin/pylonsapp_modwsgi.py')
    env.pip_requirements = 'pip-requirements-stable.txt'

def config_hmg_ckan_net_2():
    hmg_ckan_net_1()
    env.ckan_instance_name = 'hmg.ckan.net.2'
    env.hosts = ['ssh.hmg.ckan.net']
    env.config_ini_filename = 'hmg.ckan.net.ini'

def config_0(name, hosts_str='', requirements='pip-requirements-stable.txt',
        db_pass=None):
    '''Configurable configuration: fab -d gives full info.
    
    @param name: name of instance (e.g. xx.ckan.net)
    @param hosts_str: hosts to run on (--host does not work correctly).
        Defaults to name if not supplied.
    @param requirements: pip requirements to use (defaults to
        pip-requirements-stable.txt)
    @param db_pass: password to use when setting up db user (if needed)
    '''
    env.user = 'okfn'
    if hosts_str:
        env.hosts = hosts_str.split()
    if not hosts_str and not env.hosts:
        env.hosts = [name]
    env.ckan_instance_name = name
    env.base_dir = '/home/%s/var/srvc' % env.user
    env.config_ini_filename = '%s.ini' % name
    env.pip_requirements = requirements
    env.db_pass = db_pass
    
def _setup():
    def _default(key, value):
        if not hasattr(env, key):
            setattr(env, key, value)
    _default('config_ini_filename', '%s.ini' % env.ckan_instance_name)
    _default('instance_path', os.path.join(env.base_dir,
        env.ckan_instance_name))
    _default('local_backup_dir', os.path.expanduser(env.local_backup_dir))
    _default('pyenv_dir', os.path.join(env.instance_path, 'pyenv'))
    _default('serve_url', env.ckan_instance_name)
    _default('wsgi_script_filepath', os.path.join(env.pyenv_dir, 'bin', '%s.py'
        % env.ckan_instance_name))
    _default('who_ini_filepath', os.path.join(env.pyenv_dir, 'src', 'ckan',
        'who.ini'))
    _default('db_user', env.user)
    _default('db_name', env.ckan_instance_name)

def deploy():
    '''Deploy app on server. Keeps existing config files.'''
    assert env.ckan_instance_name
    assert env.base_dir
    _setup()
    _mkdir(env.instance_path)
    pip_req = env.ckan_repo + env.pip_requirements
    with cd(env.instance_path):

        # get latest pip-requirements.txt
        latest_pip_file = urllib2.urlopen(pip_req)
        tmp_pip_requirements_filepath = os.path.join('/tmp', env.pip_requirements)
        local_pip_file = open(tmp_pip_requirements_filepath, 'w')
        local_pip_file.write(latest_pip_file.read())
        local_pip_file.close()
        remote_pip_filepath = os.path.join(env.instance_path, env.pip_requirements)
        put(tmp_pip_requirements_filepath, remote_pip_filepath)
        assert exists(remote_pip_filepath)

        # create python environment
        if not exists(env.pyenv_dir):
            _run_in_cmd_pyenv('virtualenv %s' % env.pyenv_dir)
        else:
            print 'Virtualenv already exists: %s' % env.pyenv_dir
        _run_in_cmd_pyenv('pip -E %s install -r %s' % (env.pyenv_dir, env.pip_requirements))

        # create config ini file
        if not exists(env.config_ini_filename):
            # paster make-config doesn't overwrite if ini already exists
            _run_in_pyenv('paster make-config --no-interactive ckan %s' % env.config_ini_filename)
            dburi = '^sqlalchemy.url.*'
            # e.g. 'postgres://tester:pass@localhost/ckantest3'
            newdburi = 'sqlalchemy.url = postgres://%s:%s@localhost/%s' % (
                    env.db_user, env.db_pass, env.db_name)
            # sed does not find the path if not absolute (!)
            config_path = os.path.join(env.instance_path, env.config_ini_filename)
            sed(config_path, dburi, newdburi, backup='')
            setup_db()
            _run_in_pyenv('paster --plugin ckan db create --config %s' % env.config_ini_filename)
            _run_in_pyenv('paster --plugin ckan db init --config %s' % env.config_ini_filename)
        else:
            print 'Config file already exists: %s/%s' % (env.instance_path, env.config_ini_filename)
            _run_in_pyenv('paster --plugin ckan db upgrade --config %s' % env.config_ini_filename)
            _run_in_pyenv('paster --plugin ckan db init --config %s' % env.config_ini_filename)

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
        provided load if from ckan config using _get_db_config()
    '''
    if not db_details:
        db_details = _get_db_config()
    dbname = db_details['db_name']
    output = sudo('psql -l', user='postgres')
    if dbname in output:
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

def backup():
    'Backup database'
    _setup()
    if hasattr(env, 'backup_dir'):
        backup_dir = env.backup_dir
    else:
        backup_dir = os.path.join(env.base_dir, 'backup')
    _mkdir(backup_dir)
    backup_filepath = _get_unique_filepath(backup_dir, exists, 'pg_dump')

    with cd(env.instance_path):
        assert exists(env.config_ini_filename), "Can't find config file: %s/%s" % (env.instance_path, env.config_ini_filename)
    db_details = _get_db_config()
    assert db_details['db_type'] == 'postgres'
    run('export PGPASSWORD=%s&&pg_dump -U %s -D %s -h %s> %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_name'], db_details['db_host'], backup_filepath), shell=False)
    assert exists(backup_filepath)
    run('ls -l %s' % backup_filepath)
    # copy backup locally
    if env.host_string != 'localhost':
        local_backup_dir = os.path.join(env.local_backup_dir, env.host_string)
        if not os.path.exists(local_backup_dir):
            os.makedirs(local_backup_dir)
        get(backup_filepath, local_backup_dir)

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
    assert db_details['db_type'] == 'postgres'
    run('export PGPASSWORD=%s&&psql -U %s -d %s -h %s -f %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_name'], db_details['db_host'], pg_dump_filepath), shell=False)
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
    put(localpath, remotepath)


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
    assert exists(ini_filepath)
    output = run('grep -E "^%s" %s' % (key, ini_filepath))
    lines = output.split('\n')
    assert len(lines) == 1, 'Difficulty finding key %s in config %s:\n%s' % (key, ini_filepath, output)
    value = re.match('^%s[^=]=\s*(.*)' % key, lines[0]).groups()[0]
    return value

def _get_db_config():
    url = _get_ini_value('sqlalchemy.url')
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):(?P<db_pass>[^@]*)@(?P<db_host>\w*)/(?P<db_name>[\w.-]*)', url).groupdict()
    return db_details

def _get_pylons_cache_dir():
    cache_dir = _get_ini_value('cache_dir')
    # e.g. '%(here)s/data'
    return cache_dir % {'here':env.instance_path}

def _get_open_id_store_dir():
    store_file_path = _get_ini_value('store_file_path', env.who_ini_filepath)
    # e.g. '%(here)s/sstore'
    return store_file_path % {'here':env.instance_path}
    

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
        
def _run_in_pyenv(command):
    '''For running commands that are installed the instance\'s python
    environment'''
    activate_path = os.path.join(env.pyenv_dir, 'bin', 'activate')
    run('source %s&&%s' % (activate_path, command))

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
