Production Deployment
=====================

Here's an example for deploying ckan to http://demo.ckan.net/ via Apache.

1. Ideally setup the server with Ubuntu.


2. Ensure these packages are installed:

  * mercurial             Source control
  * python                Python interpreter
  * apache2               Web server
  * libapache2-mod-python Apache module for python
  * libapache2-mod-wsgi   Apache module for WSGI
  * postgresql            PostgreSQL database
  * libpq-dev             PostgreSQL library
  * python-psycopg2       PostgreSQL python module
  * python-virtualenv     Python virtual environment sandboxing


3. Create a python virtual environment

In a general user's home directory::

  $ mkdir demo.ckan.net
  $ cd demo.ckan.net
  $ virtualenv pyenv
  $ . pyenv/bin/activate


4. Install code and dependent packages into the environment

For the most recent version use::

  $ wget http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt

Or for version xxx::

  $ wget http://knowledgeforge.net/ckan/hg/raw-file/ckan-xxx/pip-requirements.txt

And install:
  $ pip -E pyenv install -r pip-requirements.txt 


5. Setup a PostgreSQL database::

  $ sudo su postgres
  $ createuser -S -D -R -P USER
  Replace USER with the unix username whose home directory has the ckan install.
  It should prompt you for a new password for the CKAN data in the database.
  $ createdb -O USER ckandemo
  $ exit


6. Setup Paster with the database::

    $ paster make-config ckan demo.ckan.net.ini

Now edit demo.ckan.net.ini to set the sqlalchemy.url database connection
information using values from previous step.


7. Initialise Database::

    $ paster db init --config demo.ckan.net.ini


9. Create the Pylons WSGI script

Create a file ~/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py as follows::

    import os
    here = os.path.abspath(os.path.dirname(__file__))
    activate_this = os.path.join(here, 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
    from paste.deploy import loadapp
    application = loadapp('config:/home/USER/demo.ckan.net/demo.ckan.net.ini')


10. Setup Apache with Ckan

Create file /etc/apache2/sites-enabled/demo.ckan.net as follows::

    <VirtualHost *:80>
        ServerName demo.ckan.net
        ServerAlias demo.ckan.net

        Alias /dump/ /home/USER/demo.ckan.net/dumps/

        # Disable the mod_python handler for static files
        <Location /dump>
            SetHandler None
            Options +Indexes
        </Location>

        WSGIScriptAlias / /home/USER/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py
        # pass authorization info on (needed for rest api)
        WSGIPassAuthorization On

        ErrorLog /var/log/apache2/ckan.net.error.log
        CustomLog /var/log/apache2/ckan.net.custom.log combined
    </VirtualHost>

Still in ~/demo.ckan.net directory::

    $ mkdir data
    $ chmod g+w -R data
    $ sudo chgrp -R www-data data
    $ ln -s pyenv/src/ckan/who.ini ./


11. Restart Apache and browse website at http://demo.ckan.net/

