============
Installation
============

These are instructions to get developing with CKAN. Instructions for deploying
CKAN to a server are at: :doc:`deployment` (doc/deployment.rst).

Before you start it may be worth checking CKAN has passed the auto build and
tests. See: http://buildbot.okfn.org/waterfall


1. Ensure these packages are installed:

   =====================  ===============================================
   Package                Description
   =====================  ===============================================
   mercurial              Source control
   python-dev             Python interpreter v2.5 - v2.7 and dev headers
   postgresql             PostgreSQL database
   libpq-dev              PostgreSQL library
   python-psycopg2        PostgreSQL python module
   libxml2-dev            XML library development files
   libxslt-dev            XSLT library development files
   python-virtualenv      Python virtual environments
   wget                   Command line tool for downloading from the web
   build-essential        Tools for building source code
   git-core               Git source control (for getting MarkupSafe src)
   subversion             Subversion source control (for pyutilib)
   =====================  ===============================================

   For Ubuntu you can install these like so:
   
   ::
   
       sudo apt-get install build-essential libxml2-dev libxslt-dev 
       sudo apt-get install wget mercurial postgresql libpq-dev git-core
       sudo apt-get install python-dev python-psycopg2 python-virtualenv
       sudo apt-get install subversion
   
2. Create a python virtual environment
   
   In your home directory run the command below. It is currently important to
   call your virtual environment ``pyenv`` so that the automated deployment tools
   work correctly.
   
   ::
   
       cd ~
       virtualenv pyenv
   
   .. tip ::
   
       If you don't have a ``python-virtualenv`` package in your distribution
       you can get a ``virtualenv.py`` script from within the 
       `virtualenv source distribution <http://pypi.python.org/pypi/virtualenv/>`_
       and then run ``python virtualenv.py pyenv`` instead.
   
       To help with automatically installing CKAN dependencies we use a tool
       called ``pip``. Make sure you have activated your environment (see step 3)
       and then install it from an activated shell like this:
   
       ::
   
           easy_install pip
   
3. Activate your virtual environment

   To work with CKAN it is best to adjust your shell settings so that your
   shell uses the virtual environment you just created. You can do this like
   so:

   ::

       . pyenv/bin/activate

   When your shell is activated you will see the prompt change to something
   like this:

   ::

       (pyenv)[ckan@host ~/]$

   An activated shell looks in your virtual environment first when choosing
   which commands to run. If you enter ``python`` now it will actually 
   run ``~/pyenv/bin/python`` which is what you want.

4. Install CKAN code and required Python packages into the new environment

   First you'll need to install CKAN. For the latest version run:

   ::

       pip install --ignore-installed -e hg+http://bitbucket.org/okfn/ckan#egg=ckan

   CKAN has a set of dependencies it requires which you should install too:

   ::

       pip install --ignore-installed -r pyenv/src/ckan/requires/lucid_missing.txt -r pyenv/src/ckan/requires/lucid_conflict.txt

   The ``--ignore-installed`` option ensures ``pip`` installs software into
   this virtual environment even if it is already present on the system.

   If you are using Ubuntu Lucid you can install the rest of the dependencies
   from the system versions like this:

   ::

       sudo apt-get install python-psycopg2 python-lxml python-sphinx 
       sudo apt-get install python-pylons python-formalchemy python-repoze.who
       sudo apt-get install python-repoze.who-plugins python-tempita python-zope.interface
       
   If you are not using Ubuntu Lucid you'll still need to install all the
   dependencies that would have been met in the ``apt-get install`` command
   at the start. You can do so like this:

   ::

       pip install --ignore-installed -r pyenv/src/ckan/requires/lucid_present.txt
   
   This will take a **long** time. Particularly the install of the ``lxml``
   package.

   At this point you will need to deactivate and then re-activate your
   virtual environment to ensure that all the scripts point to the correct
   locations:

   ::
   
       deactivate
       . pyenv/bin/activate

5. Setup a PostgreSQL database

  List existing databases:

  ::

      psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or 
  internationalisation may be a problem. Since changing the encoding of PostgreSQL
  may mean deleting existing databases, it is suggested that this is fixed before
  continuing with the CKAN install.

  Next you'll need to create a database user if one doesn't already exist.

  .. tip ::

      If you choose a database name, user or password which are different from those 
      suggested below then you'll need to update the configuration file you'll create in
      the next step.

  Here we choose ``ckantest`` as the database and ``ckanuser`` as the user:

  ::

      sudo -u postgres createuser -S -D -R -P ckantest

  It should prompt you for a new password for the CKAN data in the database.
  It is suggested you enter ``pass`` for the password.

  Now create the database, which we'll call ``ckantest`` (the last argument):

  ::

      sudo -u postgres createdb -O ckantest ckantest

6. Create a CKAN config file

  Make sure you are in an activated environment (see step 3) so that Python
  Paste and other modules are put on the python path (your command prompt will
  start with ``(pyenv)`` if you have) then change into the ``ckan`` directory
  which will have been created when you installed CKAN in step 4 and create the
  config file ``development.ini`` using Paste:

  ::

      cd pyenv/src/ckan
      paster make-config ckan development.ini

  You can give your config file a different name but the tests will expect you
  to have used ``development.ini`` so it is strongly recommended you use this
  name, at least to start with.

  If you used a different database name or password when creating the database
  in step 5 you'll need to now edit ``development.ini`` and change the
  ``sqlalchemy.url`` line, filling in the database name, user and password you used.

  ::
  
      sqlalchemy.url = postgresql://ckantest:pass@localhost/ckantest

  Other configuration, such as setting the language of the site or editing the
  visual theme are described in :doc:`configuration` (doc/configuration.rst)  

  .. caution ::

     Advanced users: If you are using CKAN's fab file capability you currently need to create
     your config file as ``pyenv/ckan.net.ini`` so you will probably have 
     ignored the advice about creating a ``development.ini`` file in the 
     ``pyenv/src/ckan`` directory. This is fine but CKAN probably won't be 
     able to find your ``who.ini`` file. To fix this edit ``pyenv/ckan.net.ini``, 
     search for the line ``who.config_file = %(here)s/who.ini`` and change it
     to ``who.config_file = who.ini``.

     We are moving to a new deployment system where this incompatibility 
     will be fixed.

7. Create database tables

  Now that you have a configuration file that has the correct settings for
  your database, you'll need to create the tables. Make sure you are still in an
  activated environment with ``(pyenv)`` at the front of the command prompt and
  then from the ``pyenv/src/ckan`` directory run this command:

   ::

       paster db init

  You should see ``Initialising DB: SUCCESS``. If you are not in the
  ``pyenv/src/ckan`` directory or you don't have an activated shell, the command
  will not work.

  If the command prompts for a password it is likely you haven't set up the 
  database configuration correctly in step 6.

8. Create the cache directory

  You need to create the Pylon's cache directory specified by 'cache_dir' 
  in the config file.

  (from the ``pyenv/src/ckan`` directory):

  ::

      mkdir data


9. Run the CKAN webserver

  NB If you've started a new shell, you'll have to activate the environment
  again first - see step 3.

  (from the pyenv/src/ckan directory):

  ::

      paster serve development.ini

10. Point your web browser at: http://127.0.0.1:5000/

    The CKAN homepage should load without problems.

If you ever want to upgrade to a more recent version of CKAN, read the
``UPGRADE.txt`` file in ``pyenv/src/ckan/``.





