Production Deployment
=====================

Here's an example for deploying CKAN to http://demo.ckan.net/ via Apache.

1. Ideally setup the server with Ubuntu.


2. Ensure these packages are installed:
   (e.g. sudo apt-get install <package-name>)

   =====================  ============================================
   Package                Notes
   =====================  ============================================
   mercurial              Source control
   python                 Python interpreter
   apache2                Web server
   libapache2-mod-python  Apache module for python
   libapache2-mod-wsgi    Apache module for WSGI
   postgresql             PostgreSQL database
   libpq-dev              PostgreSQL library
   python-psycopg2        PostgreSQL python module
   python-setuptools      Python package management
   python-libxml2         Python XML library
   python-libxslt1        Python XSLT library
   libxml2-dev            XML library development files
   libxslt1-dev           XSLT library development files
   =====================  ============================================

   Now use easy_install (which comes with python-setuptools) to install
   these packages:
   (e.g. sudo easy_install <package-name>)

   =====================  ============================================
   Package                Notes
   =====================  ============================================
   python-virtualenv      Python virtual environment sandboxing
   pip                    Python installer
   =====================  ============================================

   Check that you received:

    * virtualenv v1.3 or later
    * pip v0.4 or later


NB: Instead of using these manual instructions, steps 3 to 10 can be achieved
automatically on a remote server by running the fabric deploy script on 
your local machine. You need fabric and python-dev modules installed locally.
If you don't have the ckan repo checked out locally then download the 
fabfile.py using::

  $ wget https://bitbucket.org/okfn/ckan/raw/default/fabfile.py

Now you can then do the deployment with something like::

  $ fab config_0:demo.ckan.net,hosts_str=someserver.net,db_pass=my_password deploy


3. Setup a PostgreSQL database

  List existing databases::

  $ psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or 
  internationalisation may be a problem. Since changing the encoding of Postgres
  may mean deleting existing databases, it is suggested that this is fixed before
  continuing with the CKAN install.

  Create a database user if one doesn't already exist::

  $ sudo -u postgres createuser -S -D -R -P <user>

  Replace <user> with the unix username whose home directory has the ckan install.
  It should prompt you for a new password for the CKAN data in the database.

  Now create the database::

  $ sudo -u postgres createdb -O <user> ckandemo


4. Create a python virtual environment

  In a general user's home directory::

  $ mkdir -p ~/var/srvc/demo.ckan.net
  $ cd ~/var/srvc/demo.ckan.net
  $ virtualenv pyenv
  $ . pyenv/bin/activate


5. Create the Pylons WSGI script

  Create a file ~/var/srvc/demo.ckan.net/pyenv/bin/demp.ckan.net.py as follows (editing the first couple of variables as necessary)::

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


6. Install code and dependent packages into the environment

  For the most recent stable version use::

  $ wget https://bitbucket.org/okfn/ckan/raw/default/pip-requirements-metastable.txt

  Or for the bleeding edge use::

  $ wget https://bitbucket.org/okfn/ckan/raw/default/pip-requirements.txt

  And install::

  $ pip -E pyenv install -r pip-requirements-metastable.txt 


7. Create CKAN config file

  ::

  $ paster make-config ckan demo.ckan.net.ini


8. Configure CKAN

  Edit 'demo.ckan.net.ini' and change the default values as follows:

  8.1. sqlalchemy.url

    Set the sqlalchemy.url database connection information using values from step 3.

  8.2. licenses_group_url

    Set the licenses_group_url to point to a licenses service. Options
    include: ::

      http://licenses.opendefinition.org/2.0/ckan_original
      http://licenses.opendefinition.org/2.0/all_alphabetical

    For information about creating your own licenses services, please refer to
    the Python package called 'licenses' (http://pypi.python.org/pypi/licenses).
    
  8.3. loggers
     
    CKAN can make a log file if you change the [loggers] section to this::

      [loggers]
      keys = root, ckan
      
      [handlers]
      keys = file
      
      [formatters]
      keys = generic
      
      [logger_root]
      level = INFO
      handlers = file
      
      [logger_ckan]
      level = DEBUG
      handlers = file
      qualname = ckan
      
      [handler_file]
      class = handlers.RotatingFileHandler
      formatter = generic
      level = NOTSET
      args = ('/var/log/ckan/demo.ckan.log', 'a', 2048, 3)
      
      [formatter_generic]
      format = %(asctime)s %(levelname)-5.5s [%(name)s] %(message)s


9. Initialise database

  ::

  $ . pyenv/bin/activate
  $ paster --plugin ckan db init --config demo.ckan.net.ini


10. Set some permissions for Pylons

  Whilst still in the ~/var/srvc/demo.ckan.net directory::

    $ mkdir data sstore
    $ chmod g+w -R data sstore
    $ sudo chgrp -R www-data data sstore
    $ ln -s pyenv/src/ckan/who.ini ./
  
  Also edit the who.ini configuration file to set a secret for the auth_tkt plugin.


11. Setup Apache with Ckan

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


12. Enable site in Apache

  ::

  $ sudo a2ensite demo.ckan.net


13. Restart Apache

  ::

  $ sudo /etc/init.d/apache2 restart


14. Browse website at http://demo.ckan.net/

