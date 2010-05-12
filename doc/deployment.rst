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
   =====================  ============================================

   Now use easy_install (which comes with python-setuptools) to install
   these packages:
   (e.g. sudo easy_install <package-name>)

   =====================  ============================================
   Package                Notes
   =====================  ============================================
   python-virtualenv      Python virtual environment sandboxing
   pip                    Python installer (use easy_install for this)
   =====================  ============================================

   Check that you received:

    * virtualenv v1.3 or later
    * pip v0.7.1 or later


NB: Instead of using these manual instructions, steps 3 to 9 can be achieved
automatically on a remote server by running the fabric deploy script on 
your local machine. You need fabric and python-dev modules installed locally.
If you don't have the ckan repo checked out then download the fabfile.py using::

  $ wget https://knowledgeforge.net/ckan/hg/raw-file/default/fabfile.py

Now you can then do the deployment with something like::

  $ fab config_0:demo.ckan.net,hosts_str=someserver.net,db_pass=my_password deploy


3. Setup a PostgreSQL database

  List existing databases::

  $ psql -l

  Create a user if one doesn't already exist::

  $ sudo -u postgres createuser -S -D -R -P <user>

  Replace <user> with the unix username whose home directory has the ckan install.
  It should prompt you for a new password for the CKAN data in the database.

  Now create the database::

  $ sudo -u postgres createdb -O <user> ckandemo


4. Create a python virtual environment

  In a general user's home directory::

  $ mkdir demo.ckan.net
  $ cd demo.ckan.net
  $ virtualenv pyenv
  $ . pyenv/bin/activate


5. Create the Pylons WSGI script

  Create a file ~/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py as follows::

    import os
    here = os.path.abspath(os.path.dirname(__file__))
    activate_this = os.path.join(here, 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    from paste.deploy import loadapp
    application = loadapp('config:/home/USER/demo.ckan.net/demo.ckan.net.ini')


6. Install code and dependent packages into the environment

  For the most recent version use::

  $ wget http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt

  Or for version xxx::

  $ wget http://knowledgeforge.net/ckan/hg/raw-file/ckan-xxx/pip-requirements.txt

  And install::

  $ pip -E pyenv install -r pip-requirements.txt 


7. Create paster database config file

  ::

  $ paster make-config ckan demo.ckan.net.ini


8. Edit demo.ckan.net.ini to set the sqlalchemy.url database connection
   information using values from step 3.


9. Initialise database

  ::

  $ . pyenv/bin/activate
  $ paster --plugin ckan db init --config demo.ckan.net.ini


10. Setup Apache with Ckan

  Create file /etc/apache2/sites-enabled/demo.ckan.net as follows::

    <VirtualHost *:80>
        ServerName demo.ckan.net
        ServerAlias demo.ckan.net

        WSGIScriptAlias / /home/USER/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py
        # pass authorization info on (needed for rest api)
        WSGIPassAuthorization On

        ErrorLog /var/log/apache2/ckan.net.error.log
        CustomLog /var/log/apache2/ckan.net.custom.log combined
    </VirtualHost>

  And whilst still in the ~/demo.ckan.net directory::

    $ mkdir data
    $ chmod g+w -R data
    $ sudo chgrp -R www-data data
    $ ln -s pyenv/src/ckan/who.ini ./


11. Restart Apache

  ::

  $ sudo /etc/init.d/apache2 restart

12. Browse website at http://demo.ckan.net/

