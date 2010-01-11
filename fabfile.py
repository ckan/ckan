# usage:
#   fab [host] [operation] 
# where:
#   hosts:      local:[base_dir],[instance_name]
#               local_dev:[base_dir],[instance_name]
#               test_ckan_net
#               staging_hmg_ckan_net
#   operations: deploy
#               restart_apache
#               backup
#               restore
#               restore_from_local
# Examples:
#   deploy to a local directory: fab local:~/test,test deploy
#   deploy on test machine: fab test_ckan_net deploy
from __future__ import with_statement
import os
import datetime

from fabric.api import *
from fabric.contrib.console import *
from fabric.contrib.files import *

# defaults
env.ckan_instance_name = 'test' # e.g. test.ckan.net
env.base_dir = os.getcwd() # e.g. /home/jsmith/var/srvc
env.local_backup_dir = '~/db_backup'

def local(base_dir, ckan_instance_name):
    '''Run on localhost. e.g. local:~/test,myhost.com
                            puts it at ~/test/myhost.com
                            '''
    env.hosts = ['localhost']
    env.ckan_instance_name = ckan_instance_name # e.g. 'test.ckan.net'
    env.base_dir = os.path.expanduser(base_dir)    # e.g. ~/var/srvc

def local_dev(base_dir, ckan_instance_name):
    local(base_dir, ckan_instance_name)
    env.config_ini_filename = 'development.ini'
    env.pyenv_dir = os.path.join(base_dir, 'pyenv-%s' % ckan_instance_name)
    env.serve_url = 'localhost:5000'

def staging_hmg_ckan_net():
    env.user = 'ckan1'
    env.base_dir = '/home/%s' % env.user
    env.cmd_pyenv = os.path.join(env.base_dir, 'ourenv')
    env.no_sudo = None
    env.ckan_instance_name = 'staging.hmg.ckan.net'
    env.hosts = [env.ckan_instance_name]

def test_hmg_ckan_net():
    staging_hmg_ckan_net()
    env.ckan_instance_name = 'test.hmg.ckan.net'
    env.hosts = [env.ckan_instance_name]

def hmg_ckan_net_1():
    env.user = 'ckan1'
    env.base_dir = '/home/%s' % env.user
    env.cmd_pyenv = os.path.join(env.base_dir, 'ourenv')
    env.no_sudo = None
    env.ckan_instance_name = 'hmg.ckan.net'
    env.hosts = ['hmg.ckan.net']

def hmg_ckan_net_2():
    hmg_ckan_net_1()
    env.ckan_instance_name = 'hmg.ckan.net.2'
    env.hosts = ['hmg.ckan.net']
    env.config_ini_filename = 'hmg.ckan.net.ini.2'

def test_ckan_net():
    env.user = 'okfn'
    env.ckan_instance_name = 'test.ckan.net'
    env.hosts = [env.ckan_instance_name]
    env.base_dir = '/home/%s/var/srvc' % env.user

def ckan_net():
    env.user = 'okfn'
    env.ckan_instance_name = 'ckan.net'
    env.hosts = [env.ckan_instance_name]
    env.base_dir = '/home/%s/var/srvc' % env.user
    env.config_ini_filename = 'www.ckan.net.ini'

def _setup():
    if not hasattr(env, 'config_ini_filename'):
        env.config_ini_filename = '%s.ini' % env.ckan_instance_name
    env.instance_path = os.path.join(env.base_dir, env.ckan_instance_name)
    if hasattr(env, 'local_backup_dir'):
        env.local_backup_dir = os.path.expanduser(env.local_backup_dir)
    if not hasattr(env, 'pyenv_dir'):
        env.pyenv_dir = os.path.join(env.instance_path, 'pyenv')
    if not hasattr(env, 'serve_url'):
        env.serve_url = env.ckan_instance_name

def deploy():
    '''Deploy app on server. Keeps existing config files.'''
    assert env.ckan_instance_name
    assert env.base_dir
    _setup()
    _mkdir(env.instance_path)
    pip_req = 'http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt'
    with cd(env.instance_path):
        # no-clobber ensures we overwrite existing files (as we want)
        run('wget --no-clobber --quiet %s' % pip_req)
        if not exists(env.pyenv_dir):
            _run_in_cmd_pyenv('virtualenv %s' % env.pyenv_dir)
        else:
            print 'Virtualenv already exists: %s' % env.pyenv_dir
        _run_in_cmd_pyenv('pip -E %s install -r pip-requirements.txt' % env.pyenv_dir)

        if not exists(env.config_ini_filename):
            # paster make-config doesn't overwrite if ini already exists
            _run_in_pyenv('paster make-config --no-interactive ckan %s' % env.config_ini_filename)
        else:
            print 'Config file already exists: %s/%s' % (env.instance_path, env.config_ini_filename)

        assert env.host_string != 'hmg.ckan.net', "TODO: cope with wsgi file on hmg.ckan.net"
        wsgi_script_filepath = os.path.join(env.base_dir, 'bin', '%s.py' % env.ckan_instance_name)
        if not exists(wsgi_script_filepath):
            print 'Creating WSGI script: %s' % wsgi_script_filepath
            context = {'instance_dir':env.instance_path,
                       'config_file':env.config_ini_filename,
                       } #e.g. pyenv_dir='/home/ckan1/hmg.ckan.net'
                         #     config_file = 'hmg.ckan.net.ini'
            _create_file_by_template(wsgi_script_filepath, wsgi_script, context)
            run('chmod +r %s' % wsgi_script_filepath)
        else:
            print 'WSGI script already exists: %s' % wsgi_script_filepath
        
        whoini = os.path.join(env.pyenv_dir, 'src', 'ckan', 'who.ini')
        if not exists(whoini):
            run('ln -f -s %s ./' % whoini)
        else:
            print 'Link to who.ini already exists'

        if not exists('data'):
            print 'Setting up data (pylons cache) directory'
            run('mkdir -p data')
            if hasattr(env, 'no_sudo'):
                # Doesn't need sudo
                run('chmod gu+wx -R data')
            else:
                run('chmod g+wx -R data')
                sudo('chgrp -R www-data data')
        else:
            print 'Data (pylons cache) directory already exists'

    print 'For details of remaining setup, see deployment.rst.'

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
    assert os.path.exists(pg_dump_filepath)
    pg_dump_filename = os.path.basename(pg_dump_filename)
    remote_filepath = os.path.join('/tmp', pg_dump_filename)
    put(pg_dump_filepath, remote_filepath)
    restore_from_local(remote_filepath)

def restore(pg_dump_filepath):
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


def test():
    _setup()
    with cd(env.instance_path):
        _run_in_pyenv('paster --plugin ckan test-data %s --config %s' % (env.serve_url, env.config_ini_filename))

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

def _get_db_config():
    config_ini_filepath = os.path.join(env.instance_path, env.config_ini_filename)
    assert exists(config_ini_filepath)
    output = run('grep -E "^sqlalchemy.url" %s' % config_ini_filepath)
    lines = output.split('\n')
    assert len(lines) == 1, 'Difficulty finding sqlalchemy.url in config %s:\n%s' % (config_ini_filepath, output)
    line = lines[0]
    # line e.g. 'sqlalchemy.url = postgres://tester:pass@localhost/ckantest3'
    db_details = re.match('^sqlalchemy.url[^=]=\s*(?P<db_type>\w*)://(?P<db_user>\w*):(?P<db_pass>[^@]*)@(?P<db_host>\w*)/(?P<db_name>\w*)', line).groupdict()
    return db_details

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
