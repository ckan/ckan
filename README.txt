README
++++++

Introduction
============

Comprehensive Knowledge Archive Network (CKAN) Software.

See :mod:`ckan.__long_description__` for more information.


Developer Installation
======================

These are instructions to get developing with CKAN. Instructions for deploying
CKAN to a server are at: :doc:`deployment` (doc/deployment.rst).

Before you start it may be worth checking CKAN has passed the auto build and
tests. See: http://buildbot.okfn.org/waterfall


1. Ensure these packages are installed:
   (e.g. for ubuntu: sudo apt-get install <package-name>)

   =====================  ============================================
   Package                Description
   =====================  ============================================
   mercurial              Source control
   python                 Python interpreter v2.5 - v2.7
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
   pip                    Python installer (use easy_install for this)
   =====================  ============================================

   Check that you received:

    * virtualenv v1.3 or later
    * pip v0.4 or later


2. Create a python virtual environment

  e.g. in your home directory::

  $ virtualenv pyenv


3. Install CKAN code and required Python packages into the new environment

  For the most recent version use::

  $ wget https://bitbucket.org/okfn/ckan/raw/default/pip-requirements.txt

  Or for the 'metastable' branch (used for most server installs)::

  $ wget https://bitbucket.org/okfn/ckan/raw/default/pip-requirements-metastable.txt

  And install::

  $ pip -E pyenv install -r pip-requirements.txt

  or::

  $ pip -E pyenv install -r pip-requirements-metastable.txt


4. Setup a Postgresql database

  List existing databases::

  $ psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or 
  internationalisation may be a problem. Since changing the encoding of Postgres
  may mean deleting existing databases, it is suggested that this is fixed before
  continuing with the CKAN install.

  Create a database user if one doesn't already exist. Here we choose 'ckantest'::

  $ sudo -u postgres createuser -S -D -R -P ckantest

  It should prompt you for a new password for the CKAN data in the database.
  It is suggested you enter 'pass' for the password.

  Now create the database, which we'll call 'ckantest' (the last argument)::

  $ sudo -u postgres createdb -O ckantest ckantest


5. Create a CKAN config file

  First 'activate' your environment so that Python Paste and other modules are
  put on the python path::

  $ . pyenv/bin/activate

  Now we create the config file 'development.ini' using Paste::

  $ cd pyenv/src/ckan
  $ paster make-config ckan development.ini

  Now edit development.ini and change the `sqlalchemy.url` line, filling
  in the database user and password as given in the previous step::
  
    sqlalchemy.url = postgres://ckantest:pass@localhost/ckantest

  Other configuration, such as setting the language of the site or editing the
  visual theme are described in :doc:`configuration` (doc/configuration.rst)  


6. Initialise the database

  NB If you've started a new shell, you'll have to activate the environment
  again first - see step 5.

  (from the pyenv/src/ckan directory)::

  $ paster db init

  You should see "Initialising DB: SUCCESS"


7. Create the cache directory

  You need to create the Pylon's cache directory specified by 'cache_dir' 
  in the config file.

  (from the pyenv/src/ckan directory)::

  $ mkdir data


8. Run the CKAN webserver

  NB If you've started a new shell, you'll have to activate the environment
  again first - see step 5.

  (from the pyenv/src/ckan directory)::

  $ paster serve development.ini


9. Point your web browser at: http://127.0.0.1:5000/
   The CKAN homepage should load without problem.


Test
====

Make sure you've created a config file: pyenv/ckan/development.ini 

Ensure you have activated the environment:
  $ pyenv/bin/activate

Now start the starts:
  $ nosetests pyenv/src/ckan/ckan/tests


Development
===========

CKAN is an open source project and contributions are welcome! 

There are a number of stakeholders in the direction of the project, so we discuss large changes and new features on the ckan-discuss list: http://lists.okfn.org/mailman/listinfo/ckan-discuss

New developers should aquaint themselves with the documentation (see below) and proposed patches emailed to ckan-discuss. Once they are comfortable they should request write-access to the repo.

We have policies for check-ins that ensure the build doesn't break etc. on https://knowledgeforge.net/ckan/trac#ProjectProcessesandPolicies which should be followed unless someone builds concensus to change it.


Documentation
=============

The home page for the CKAN project is: http://ckan.org

This README file is part of the Developer Documentation, viewable at:
`http://knowledgeforge.net/ckan/doc/ckan/index.html`_ and stored in the CKAN
repo at ckan/doc. 

The Developer Docs are built using `Sphinx <http://sphinx.pocoo.org/>`_:

      python setup.py build_sphinx

The docs are uploaded to packages.python.org/ckan/ and also (via dav) to
http://knowledgeforge.net/ckan/doc/ckan/ (http://knowledgeforge.net/ location
is for backwards compatability).
 

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


Copying and License
===================

This material is copyright (c) 2006-2010 Open Knowledge Foundation.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0
whose full text may be found at:

<http://www.fsf.org/licensing/licenses/agpl-3.0.html>

