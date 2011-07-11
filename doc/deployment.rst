Deployment
==========

After installing CKAN, you will want to deploy it as a production site. This section gives an example of deploying CKAN to http://demo.ckan.net/ using Apache. 

1. Prepare the server for CKAN, as described in Installation. 

2. Create a Pylons WSGI script. 

  Create a file ~/var/srvc/demo.ckan.net/pyenv/bin/demo.ckan.net.py as follows (editing the first couple of variables as necessary)::

    import os
    instance_dir = '/home/USER/var/srvc/demo.ckan.net'
    config_file = 'demo.ckan.net.ini'
    pyenv_bin_dir = os.path.join(instance_dir, 'pyenv', 'bin')
    activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    from paste.deploy import loadapp
    config_filepath = os.path.join(instance_dir, config_file)
    from paste.script.util.logging_config import fileConfig
    fileConfig(config_filepath)
    application = loadapp('config:%s' % config_filepath)

3. Initialise database

  ::

  $ . pyenv/bin/activate
  $ paster --plugin ckan db init --config demo.ckan.net.ini


4. Set some permissions for Pylons

  Whilst still in the ~/var/srvc/demo.ckan.net directory::

    $ mkdir data sstore
    $ chmod g+w -R data sstore
    $ sudo chgrp -R www-data data sstore
    $ ln -s pyenv/src/ckan/who.ini ./
  
  Also edit the who.ini configuration file to set a secret for the auth_tkt plugin. ???


5. Set up Apache with CKAN

Create file /etc/apache2/sites-available/demo.ckan.net as follows::

    <VirtualHost *:80>
        ServerName demo.ckan.net
        ServerAlias demo.ckan.net
        WSGIScriptAlias / /home/USER/var/srvc/demo.ckan.net/pyenv/bin/demo.ckan.net.py
        # pass authorization info on (needed for rest api)
        WSGIPassAuthorization On
        ErrorLog /var/log/apache2/demo.ckan.net.error.log
        CustomLog /var/log/apache2/demo.ckan.net.custom.log combined
    </VirtualHost>

6. Enable the site in Apache

  ::

  $ sudo a2ensite demo.ckan.net


7. Restart Apache

  ::

  $ sudo /etc/init.d/apache2 restart


8. Browse your new CKAN site at http://demo.ckan.net/ (assuming you have the DNS set up for this server). 

Should you have problems, check the log files specified in your Apache config and ckan oconfig. e.g. ``/var/log/apache2/demo.ckan.net.error.log`` and ``/var/log/ckan/demo.ckan.log``.
