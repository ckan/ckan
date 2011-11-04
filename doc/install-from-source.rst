=============================
Option 2: Install from Source
=============================

This section describes how to install CKAN from source. Whereas :doc:`install-from-package` requires Ubuntu 10.04, this way of installing CKAN is more flexible to work with other distributions and operating systems. Please share your experiences on our wiki: http://wiki.ckan.org/Install

This is also the option to use if you are going to develop the CKAN source.

.. warning:: This option is more complex than :doc:`install-from-package`.

There is a page of help for dealing with :doc:`common-error-messages`.

For support during installation, please contact `the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.

Install the Source
------------------

1. Ensure the required packages are installed.

   If you have access to ``apt-get``, you can install these packages as follows:

   ::

       sudo apt-get install mercurial python-dev postgresql libpq-dev 
       sudo apt-get install libxml2-dev libxslt-dev python-virtualenv
       sudo apt-get install wget build-essential git-core subversion 
       sudo apt-get install solr-jetty openjdk-6-jdk

   Otherwise, you should install these packages from source. 

   =====================  ===============================================
   Package                Description
   =====================  ===============================================
   mercurial              `Source control <http://mercurial.selenic.com/>`_
   python                 `Python v2.5-2.7 <http://www.python.org/getit/>`_
   postgresql             `PostgreSQL database <http://www.postgresql.org/download/>`_
   libpq                  `PostgreSQL library <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
   libxml2                `XML library development files <http://xmlsoft.org/>`_
   libxslt                `XSLT library development files <http://www.linuxfromscratch.org/blfs/view/6.3/general/libxslt.html>`_
   virtualenv             `Python virtual environments <http://pypi.python.org/pypi/virtualenv>`_
   wget                   `Command line tool for downloading from the web <http://www.gnu.org/s/wget/>`_
   build-essential        Tools for building source code (or up-to-date Xcode on Mac)
   git                    `Git source control (for getting MarkupSafe src) <http://book.git-scm.com/2_installing_git.html>`_
   subversion             `Subversion source control (for pyutilib) <http://subversion.apache.org/packages.html>`_
   solr                   `Search engine <http://lucene.apache.org/solr>`_
   jetty                  `HTTP server <http://jetty.codehaus.org/jetty/>`_ (used for Solr)
   openjdk-6-jdk          `OpenJDK Java library <http://openjdk.java.net/install/>`_
   =====================  ===============================================

   

2. Create a Python virtual environment.
   
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
   
3. Activate your virtual environment.

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
   run ``~/pyenv/bin/python``, not the default ``/usr/bin/python`` which is what you want for CKAN. You can install python packages install this new environment and they won't affect the default ``/usr/bin/python``. This is necessary so you can use particular versions of python packages, rather than the ones installed with default paython, and these installs do not affect other python software on your system that may not be compatible with these packages.

4. Install CKAN code and other required Python packages into the new environment.

   Choose which version of CKAN to install. Released versions are listed at https://bitbucket.org/okfn/ckan - click on the list of tags. For example: ``ckan-1.4.2``

   ::

       pip install --ignore-installed -e hg+http://bitbucket.org/okfn/ckan@ckan-1.4.2#egg=ckan

   Alternatively, if you are to develop CKAN, then you will probably want to use the latest 'bleeding edge' code. If using this version, we suggest you `check CKAN has passed the automatic tests <http://buildbot.okfn.org/waterfall>`_. Here is how to install the latest code::

       pip install --ignore-installed -e hg+http://bitbucket.org/okfn/ckan#egg=ckan

5. CKAN has a set of dependencies it requires which you should install too. These are listed in three text files: requires/lucid_*.txt, followed by WebOb explicitly.

   First we install two of the three lists of dependencies:

   ::

       pip install --ignore-installed -r pyenv/src/ckan/requires/lucid_missing.txt -r pyenv/src/ckan/requires/lucid_conflict.txt
       pip install webob==1.0.8

   The ``--ignore-installed`` option ensures ``pip`` installs software into
   this virtual environment even if it is already present on the system.

   WebOb has to be installed explicitly afterwards because by installing pylons with `--ignore-installed` you end up with a newer (incompatible) version than the one that Pylons and CKAN need.

   Now to install the remaining dependencies in requires/lucid_present.txt and you are using Ubuntu Lucid 10.04 you can install the system versions::

       sudo apt-get install python-pybabel python-psycopg2 python-lxml 
       sudo apt-get install python-sphinx python-pylons python-repoze.who 
       sudo apt-get install python-repoze.who-plugins python-tempita python-zope.interface
       
   Alternatively, if you are not using Ubuntu Lucid 10.04 you'll need to install them like this:

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

6. Setup a PostgreSQL database.

  List existing databases:

  ::

      sudo -u postgres psql -l

  It is advisable to ensure that the encoding of databases is 'UTF8', or 
  internationalisation may be a problem. Since changing the encoding of PostgreSQL
  may mean deleting existing databases, it is suggested that this is fixed before
  continuing with the CKAN install.

  Next you'll need to create a database user if one doesn't already exist.

  .. tip ::

      If you choose a database name, user or password which are different from the example values suggested below then you'll need to change the sqlalchemy.url value accordingly in the CKAN configuration file you'll create in the next step.

  Here we create a user called ``ckanuser`` and will enter ``pass`` for the password when prompted:

  ::

      sudo -u postgres createuser -S -D -R -P ckanuser

  Now create the database (owned by ``ckanuser``), which we'll call ``ckantest``:

  ::

      sudo -u postgres createdb -O ckanuser ckantest

7. Create a CKAN config file.

  Make sure you are in an activated environment (see step 3) so that Python
  Paste and other modules are put on the python path (your command prompt will
  start with ``(pyenv)`` if you have) then change into the ``ckan`` directory
  which will have been created when you installed CKAN in step 4 and create the
  CKAN config file using Paste. These instructions call it ``development.ini`` since that is the required name for running the CKAN tests. But for a server deployment then you might want to call it say after the server hostname e.g. ``test.ckan.net.ini``.

  ::

      cd pyenv/src/ckan
      paster make-config ckan development.ini

  If you used a different database name or password when creating the database
  in step 5 you'll need to now edit ``development.ini`` and change the
  ``sqlalchemy.url`` line, filling in the database name, user and password you used.

  ::
  
      sqlalchemy.url = postgresql://ckanuser:pass@localhost/ckantest

  If you're using a remote host with password authentication rather than SSL authentication, use::

      sqlalchemy.url = postgresql://<user>:<password>@<remotehost>/ckan?sslmode=disable

  .. caution ::

     Advanced users: If you have installed CKAN using the Fabric file capability (deprecated),
     your config file will be called something like ``pyenv/ckan.net.ini``. 
     This is fine but CKAN probably won't be 
     able to find your ``who.ini`` file. To fix this edit ``pyenv/ckan.net.ini``, 
     search for the line ``who.config_file = %(here)s/who.ini`` and change it
     to ``who.config_file = who.ini``.

     We are moving to a new deployment system where this incompatibility 
     will be fixed.

8. Create database tables.

  Now that you have a configuration file that has the correct settings for
  your database, you'll need to create the tables. Make sure you are still in an
  activated environment with ``(pyenv)`` at the front of the command prompt and
  then from the ``pyenv/src/ckan`` directory run this command.

  If your config file is called development.ini:

   ::

       paster --plugin=ckan db init

  or if your config file is something else, you need to specify it. e.g.::

       paster --plugin=ckan db init --config=test.ckan.net.ini

  You should see ``Initialising DB: SUCCESS``. 

  If the command prompts for a password it is likely you haven't set up the 
  database configuration correctly in step 6.

9. Create the cache directory.

  You need to create the Pylon's cache directory specified by 'cache_dir' 
  in the config file.

  (from the ``pyenv/src/ckan`` directory):

  ::

      mkdir data


10. Setup Solr.

   Edit the jetty config file (/etc/default/jetty by default on Ubuntu),
   changing the following:

   ::

       NO_START=0            # (line 4)
       JETTY_HOST=127.0.0.1  # (line 15)
       JETTY_PORT=8983       # (line 18)

   Then replace Solr's schema.xml file with a symlink to the one in the CKAN source (Note: The path ``~/pyenv/src/ckan/ckan/config/schema.xml`` will probably need to be to be adjusted for your system. Also ensure it is an absolute path.)

   ::

       sudo mv /usr/share/solr/conf/schema.xml /usr/share/solr/conf/schema.xml.bak
       sudo ln -s ~/pyenv/src/ckan/ckan/config/schema.xml /usr/share/solr/conf/schema.xml

   Set appropriate values for the ``ckan.site_id`` and ``solr_url`` config variables in your CKAN config file:

   ::

       ckan.site_id=my_ckan_instance
       solr_url=http://127.0.0.1:8983/solr

   You should now be able to start Solr:

   ::

       sudo service jetty start

  .. note:: If you get the message `Could not start Jetty servlet engine because no Java Development Kit (JDK) was found.` then you will have to edit /etc/profile and add this line to the end such as this to the end (adjusting the path for your machine's jdk install)::

       JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/

    Now run::

       export JAVA_HOME
       sudo service jetty start


  Now you should check Solr is running ok by browsing: http://localhost:8983/solr/

  For more information on Solr setup and configuration, see the CKAN wiki: http://wiki.ckan.net/Solr_Search


11. Run the CKAN webserver.

  NB If you've started a new shell, you'll have to activate the environment
  again first - see step 3.

  (from the ``pyenv/src/ckan`` directory):

  ::

      paster serve development.ini

12. Point your web browser at: http://127.0.0.1:5000/

    The CKAN homepage should load.

Finally, make sure that tests pass, as described in :ref:`basic-tests`.

You can now proceed to :doc:`post-installation`.
