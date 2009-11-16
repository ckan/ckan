README
++++++

Introduction
============

Comprehensive Knowledge Archive Network (CKAN) Software.

See ckan.__long_description__ for more information.


Developer Installation
======================

1. Get the code and install it:

   We recommend installing using pip and virtualenv::
   
      # grab the install requirements from the ckan mercurial repo
      wget http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt
      # create a virtualenv to install into
      virtualenv --no-site-packages pyenv-ckan
      # install using pip-requirements
      pip -E pyenv-ckan install -r pip-requirements.txt

3. Make a config file as follows::

      # NB: you need to activate the repository
      paster --plugin ckan make-config ckan {your-config.ini}

4. Tweak the config file as appropriate and then setup the application::

      paster --plugin ckan setup-app {your-config.ini}

   NB: you'll need to setup a database -- see sqlalchemy.url config option. We
   support any database supported by sqlalchemy.

5. Run the webserver::

      paster serve {your-config.ini} 

6. Point your browser at: localhost:5000 (if you set a different port in your
   config file then youl will need to change 5000 to whatever port value you
   chose).


Server Installation
===================

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

In a general user's home directory:
$ mkdir -p var/srvc/demo.ckan.net
$ cd var/srvc/demo.ckan.net
$ virtualenv pyenv
$ . pyenv/bin/activate


4. Install code and dependent packages into the environment

For the most recent version use:
$ wget http://knowledgeforge.net/ckan/hg/raw-file/tip/pip-requirements.txt
(or use curl instead of wget if that's not installed)
Or for version 0.10:
$ wget http://knowledgeforge.net/ckan/hg/raw-file/ckan-0.10/pip-requirements.txt
For version 0.10 it is also necessary to edit the pip-requirements.txt and
change: okfn/vdm#egg=vdm to okfn/vdm#egg=vdm==0.5
and: ckan/hg#egg=ckan to ckan/hg#egg=ckan==0.10

$ pip -E pyenv install -r pip-requirements.txt 


5. Setup the PostgreSQL database

$ sudo su postgres
$ createuser -S -D -R -P USER
Replace USER with the unix username whose home directory has the ckan install.
It should prompt you for a new password for the CKAN data in the database.
$ createdb ckandemo
$ exit


6. Setup Paster with the database

$ paster make-config ckan demo.ckan.net.ini
Now edit demo.ckan.net.ini . In the section "[app:main]" add this line:
sqlalchemy.url = postgres://USER:PASSWORD@localhost/ckandemo
Replace USER and PASSWORD with the values entered into PostgreSQL setup in the
previous step.


7. Initialise Database

$ paster db clean --config demo.ckan.net.ini
$ paster db init --config demo.ckan.net.ini


8. Run locally

$ paster serve --reload demo.ckan.net.ini


9. Create the Pylons WSGI script

Create a file ~/var/srvc/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py as follows:

import os
here = os.path.abspath(os.path.dirname(__file__))
activate_this = os.path.join(here, 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))
from paste.deploy import loadapp
application = loadapp('config:/home/USER/var/srvc/demo.ckan.net/demo.ckan.net.ini')


10. Setup Apache with Ckan

Create file /etc/apache2/sites-enabled/demo.ckan.net as follows:
<VirtualHost *:80>
    ServerName demo.ckan.net
    ServerAlias demo.ckan.net

    Alias /dump/ /home/USER/var/srvc/demo.ckan.net/dumps/

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>

    WSGIScriptAlias / /home/USER/var/srvc/demo.ckan.net/pyenv/bin/pylonsapp_modwsgi.py
    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

    ErrorLog /var/log/apache2/ckan.net.error.log
    CustomLog /var/log/apache2/ckan.net.custom.log combined
</VirtualHost>

(still in ~/var/srvc/demo.ckan.net directory)
$ mkdir data
$ chmod g+w -R data
$ sudo chgrp -R www-data data
$ cp pyenv/src/ckan/who.ini ./


11. Run Apache

$ sudo /etc/init.d/apache2 start
Now browse website at http://demo.ckan.net/


Access password
===============

When access to hmg.ckan.net has beenrestricted using the confirmation in ~/etc/

To add a new user:

    htpasswd -m etc/hmg.ckan.net.passwd hmg

Then add that user to the groups file (etc/hmg.ckan.net.groups)


Contributors
============

  * Rufus Pollock <rufus [at] rufuspollock [dot] org>
  * David Read
  * John Bywater
  * Nick Stenning (css and js)

Also especial thanks to the following projects without whom this would not have
been possible:

  * CKAN logo: "angry hamster" http://www.maedelmaedel.com/ and
    http://www.villainous.biz/
  * famfamfam.com for silk icons <http://www.famfamfam.com/lab/icons/silk/>
  * Pylons: <http://pylonshq.com/>
  * Python: <http://www.python.org>


Test
====

Make sure you've created a config called development.ini, then:: 

    nosetests ckan/tests


Copying and License
===================

This material is open and licensed under the MIT license as follows:

Copyright (c) 2006-2009 Open Knowledge Foundation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

