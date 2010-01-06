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

def test_ckan_net():
    env.user = 'okfn'
    env.hosts = ['test.ckan.net']
    env.ckan_instance_name = 'test.ckan.net'
    env.base_dir = '/home/%s/var/srvc' % env.user

def live():
    # config.fab_user = 'live_user_name'
    # config.fab_hosts = ['www1.yourserver.com', 'www2.yourserver.com', 'www3.yourserver.com']
    pass

def deploy():
    '''Deploy app on server'''
    instance_path = os.path.join(env.base_dir, env.ckan_instance_name)
    run('mkdir -p %s' % instance_path) 
    pip_req = 'http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt'
    pyenv_dir = os.path.join(instance_path, 'pyenv')
    with cd(instance_path):
        # no-clobber ensures we overwrite existing files (as we want)
        run('wget --no-clobber --quiet %s' % pip_req)
        run('virtualenv pyenv')
        run('pip -E %s install -r pip-requirements.txt' % pyenv_dir)

        ini_filename = '%s.ini' % env.ckan_instance_name
        # paster make-config doesn't overwrite if ini already exists
        virtualenv('paster make-config --no-interactive ckan %s' % ini_filename) 

        wsgi_script_filepath = os.path.join(env.base_dir, 'bin', '%s.py' % env.ckan_instance_name)
        context = {'pyenv_dir':instance_path,
                   'config_file':ini_filename,
                   } #e.g. pyenv_dir='/home/ckan1/hmg.ckan.net'
                     #     config_file = 'hmg.ckan.net.ini'
        create_file_by_template(wsgi_script_filepath, wsgi_script, context)
        run('chmod +r %s' % wsgi_script_filepath)
        
        whoini = os.path.join(pyenv_dir, 'src', 'ckan', 'who.ini')
        run('ln -f -s %s ./' % whoini)
        run('mkdir -p data')
        run('chmod g+wx -R data')
        sudo('chgrp -R www-data data')

    print 'For details of remaining setup, see deployment.rst.'

def virtualenv(command):
    run('source pyenv/bin/activate&&' + command)

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
pyenv_dir = '%(pyenv_dir)s'
config_file = '%(config_file)s'
pyenv_bin_dir = os.path.join(pyenv_dir, 'pyenv', 'bin')
activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))
from paste.deploy import loadapp
config_filepath = os.path.join(pyenv_dir, config_file)
application = loadapp('config:%%s' %% config_filepath)
"""
