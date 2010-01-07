# usage:
#   deploy to a local directory: fab local:~/test,test deploy
#   deploy on test machine: fab test_ckan_net deploy

from __future__ import with_statement
import os

from fabric.api import *
from fabric.contrib.files import *

# default to local machine's current dir
env.ckan_instance_name = 'test' # e.g. test.ckan.net
env.base_dir = os.getcwd() # e.g. /home/jsmith/var/srvc

def local(base_dir, ckan_instance_name):
    env.hosts = ['localhost']
    env.ckan_instance_name = ckan_instance_name # e.g. 'test.ckan.net'
    env.base_dir = os.path.expanduser(base_dir)    # e.g. ~/var/srvc

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

def test_ckan_net():
    env.user = 'okfn'
    env.ckan_instance_name = 'test.ckan.net'
    env.hosts = [env.ckan_instance_name]
    env.base_dir = '/home/%s/var/srvc' % env.user

def deploy():
    '''Deploy app on server. Config files already there will not be overwritten.'''
    assert env.ckan_instance_name
    assert env.base_dir
    instance_path = os.path.join(env.base_dir, env.ckan_instance_name)
    if not exists(instance_path):
        run('mkdir -p %s' % instance_path)
    else:
        print 'Instance path already exists: %s' % instance_path
    pip_req = 'http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt'
    env.pyenv_dir = os.path.join(instance_path, 'pyenv')
    with cd(instance_path):
        # no-clobber ensures we overwrite existing files (as we want)
        run('wget --no-clobber --quiet %s' % pip_req)
        if not exists(env.pyenv_dir):
            run_in_cmd_pyenv('virtualenv %s' % env.pyenv_dir)
        else:
            print 'Virtualenv already exists: %s' % env.pyenv_dir
        run_in_cmd_pyenv('pip -E %s install -r pip-requirements.txt' % env.pyenv_dir)

        config_ini_filename = '%s.ini' % env.ckan_instance_name
        if not exists(config_ini_filename):
            # paster make-config doesn't overwrite if ini already exists
            run_in_pyenv('paster make-config --no-interactive ckan %s' % config_ini_filename)
        else:
            print 'Config file already exists: %s/%s' % (instance_path, config_ini_filename)

        wsgi_script_filepath = os.path.join(env.base_dir, 'bin', '%s.py' % env.ckan_instance_name)
        if not exists(wsgi_script_filepath):
            print 'Creating WSGI script: %s' % wsgi_script_filepath
            context = {'instance_dir':instance_path,
                       'config_file':config_ini_filename,
                       } #e.g. pyenv_dir='/home/ckan1/hmg.ckan.net'
                         #     config_file = 'hmg.ckan.net.ini'
            create_file_by_template(wsgi_script_filepath, wsgi_script, context)
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

def run_in_pyenv(command):
    '''For running commands that are installed the instance\'s python
    environment'''
    activate_path = os.path.join(env.pyenv_dir, 'bin', 'activate')
    run('source %s&&%s' % (activate_path, command))

def run_in_cmd_pyenv(command):
    '''For running commands that are installed in a specific python
    environment specified by env.cmd_pyenv'''
    if hasattr(env, 'cmd_pyenv'):
        activate_path = os.path.join(env.cmd_pyenv, 'bin', 'activate')
        command = 'source %s&&%s' % (activate_path, command)
    run(command)

def create_file_by_template(destination_filepath, template, template_context):
    run('mkdir -p %s' % os.path.dirname(destination_filepath))
    upload_template_buffer(template, destination_filepath, template_context)

def upload_template_buffer(template, destination, context=None, use_sudo=False):
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
