=============================
Option 2: Install from Source
=============================

This section describes how to install CKAN from source. Although
:doc:`install-from-package` is simpler, it requires Ubuntu 10.04. Installing
CKAN from source works with Ubuntu 10.04, with other versions of Ubuntu (e.g.
12.04) and with other operating systems (e.g. RedHat, Fedora, CentOS, OS X). If
you install CKAN from source on your own operating system, please share your
experiences on our `How to Install CKAN <https://github.com/okfn/ckan/wiki/How-to-Install-CKAN>`_
wiki page.

From source is also the right installation method for developers who want to
work on CKAN.

If you run into problems, see :doc:`common-error-messages`.

1. Install the required packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're using a Debian-based operating system (such as Ubuntu) install the
required packages with this command::

    sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core solr-jetty openjdk-6-jdk

If you're not using a Debian-based operating system, find the best way to
install the following packages on your operating system (see
our `How to Install CKAN <https://github.com/okfn/ckan/wiki/How-to-Install-CKAN>`_
wiki page for help):

=====================  ===============================================
Package                Description
=====================  ===============================================
Python                 `The Python programming language, v2.6 or 2.7 <http://www.python.org/getit/>`_
PostgreSQL             `The PostgreSQL database system, v8.4 or newer <http://www.postgresql.org/download/>`_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
pip                    `A tool for installing and managing Python packages <http://www.pip-installer.org>`_
virtualenv             `The virtual Python environment builder <http://pypi.python.org/pypi/virtualenv>`_
Git                    `A distributed version control system <http://book.git-scm.com/2_installing_git.html>`_
Apache Solr                   `A search platform <http://lucene.apache.org/solr>`_
Jetty                  `An HTTP server <http://jetty.codehaus.org/jetty/>`_ (used for Solr)
OpenJDK 6 JDK          `The Java Development Kit <http://openjdk.java.net/install/>`_
=====================  ===============================================

Naming Conventions and Filesystem Layout
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Especially when managing many sites, it's useful to decide on a naming
convention and stick to it.  In this example, we'll create a fictional CKAN
website ``http://masaq.ckanhosted.com`` (an online datahub for the citizens of
Masaq). We'll use the site's name ``masaq`` throughout the
setup: as the names of the site's database and database user, as the
``ckan.site_id`` in the site's configuration file, as the site's WSGI process
name and group, etc.

The site's name is also used as the directory names for the site's
virtualenv and config files directories. As you'll see, the directories
created by the commands given in these instructions are layed out like this:

``/usr/lib/ckan/masaq/``
  The directory containing the site's virtualenv.

``/etc/ckan/masaq/``
  The directory containing the site's configuration files.

``/etc/apache2/sites-available/masaq``
  The site's Apache config file.

``/var/log/apache2/masaq.error.log``
  The site's Apache error log file.

This recommended filesystem layout allows more virtualenvs for more CKAN
sites to be created later, if you want to install more CKAN sites on the
same machine. The virtualenvs and config files for further sites would be created in
subdirectories named after those sites, for example::

  /usr/lib/ckan/
    masaq/      <-- virtualenv for masaq.ckanhosted.com
      ...
    chiark/     <-- virtualenv for chiark.ckanhosted.com
      ...
  /etc/ckan/
    masaq/      <-- Config files for masaq.ckanhosted.com
      apache.wsgi
      development.ini
      production.ini
    chiark/     <-- Config files for chiark.ckanhosted.com
      apache.wsgi
      development.ini
      production.ini
  /etc/apache2/sites-available/
    masaq      <-- Apache config file for masaq.ckanhosted.com
    chiark     <-- Apache config file for chiark.ckanhosted.com
  /var/log/apache2/
    masaq.error.log      <-- Error log for masaq.ckanhosted.com
    chiark.error.log     <-- Error log for chiark.ckanhosted.com


2. Install CKAN into a virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

a. Create a Python virtual environment (virtualenv) to install CKAN into, and
activate it. In the second command, replace ``seanh`` with your own username::

       sudo mkdir /usr/lib/ckan
       sudo chown seanh /usr/lib/ckan/
       virtualenv --no-site-packages /usr/lib/ckan/masaq
       . /usr/lib/ckan/masaq/bin/activate

.. important::

   The final command above activates your virtualenv. The virtualenv has to
   remain active for the rest of the installation and deployment process,
   or commands will fail. You can tell when the virtualenv is active because
   its name appears in front of your shell prompt, something like this::

     (masaq) $ _

   For example, if you logout and login again, or if you close your terminal
   window and open it again, your virtualenv will no longer be activated. You
   can always reactivate the virtualenv with this command::

     . /usr/lib/ckan/masaq/bin/activate

.. tip::

   If you're installing CKAN for development and want it to be installed in
   your home directory, you can symlink the directories used in this
   documentation to your home directory. This way, you can copy-paste the
   example commands from this documentation without having to modify them, and
   still have CKAN installed in your home directory::

     mkdir -p ~/ckan/lib
     sudo ln -s ~/ckan/lib /usr/lib/ckan
     mkdir -p ~/ckan/etc
     sudo ln -s ~/ckan/etc /etc/ckan

b. Install the CKAN source code into your virtualenv. To install the latest
   development version of CKAN (the most recent commit on the master branch of
   the CKAN git repository), run::

       pip install -e 'git+https://github.com/okfn/ckan.git#egg=ckan'

   Alternatively, to install a specific version such as CKAN 2.0, run::

       pip install -e 'git+https://github.com/okfn/ckan.git@ckan-2.0#egg=ckan'

c. Install the Python modules that CKAN requires into your virtualenv::

       pip install -r /usr/lib/ckan/masaq/src/ckan/pip-requirements.txt

d. Deactivate and reactivate your virtualenv, to make sure you're using the
   virtualenv's copies of commands like ``paster`` rather than any system-wide
   installed copies::

    deactivate
    . /usr/lib/ckan/masaq/bin/activate


3. Setup a PostgreSQL database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List existing databases::

    sudo -u postgres psql -l

Check that the encoding of databases is 'UTF-8', if not internationalisation may
be a problem. Since changing the encoding of PostgreSQL may mean deleting
existing databases, it is suggested that this is fixed before continuing with
the CKAN install.

Next you'll need to create a database user if one doesn't already exist.

Create a new PostgreSQL database user called ``masaq``, and
enter a password for the account when prompted. You'll need this password
later::

    sudo -u postgres createuser -S -D -R -P masaq

Create a new PostgreSQL database, also called ``masaq``, owned
by the database user you just created::

    sudo -u postgres createdb -O masaq masaq -E utf-8


4. Create a CKAN config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a directory to contain the site's config files. In the second command,
replace ``seanh`` with your own username::

    sudo mkdir -p /etc/ckan/masaq
    sudo chown -R seanh /etc/ckan/

Change to the ``ckan`` directory and create a CKAN config file::

    cd /usr/lib/ckan/masaq/src/ckan
    paster make-config ckan /etc/ckan/masaq/development.ini

.. tip::

   In this example we created a CKAN config file named ``development.ini``.
   This config file name is conventionally used when running CKAN for
   development. When deploying a production website with CKAN, it's
   conventional to create another config file called ``production.ini`` (with
   the command: ``paster make-config ckan production.ini``).

Edit the ``development.ini`` file in a text editor, changing the following
options::

sqlalchemy.url
  This should refer to the database we created in `3. Setup a PostgreSQL
  database`_ above::

    sqlalchemy.url = postgresql://masaq:pass@localhost/masaq

  Replace ``pass`` with the password that you created in `3. Setup a
  PostgreSQL database`_ above.

  .. tip ::

     If you're using a remote host with password authentication rather than SSL
     authentication, use::

       sqlalchemy.url = postgresql://masaq:pass@<remotehost>/masaq?sslmode=disable

site_id
  Each CKAN site should have a unique ``site_id``, for example::

   ckan.site_id = masaq


5. Setup Solr
~~~~~~~~~~~~~

Follow the instructions in :ref:`solr-single` or :ref:`solr-multi-core` to
setup Solr, then change the ``solr_url`` option in your CKAN config file to
point to your Solr server, for example::

       solr_url=http://127.0.0.1:8983/solr

6. Create database tables
~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have a configuration file that has the correct settings for your
database, you can create the database tables::

    cd /usr/lib/ckan/masaq/src/ckan
    paster --plugin=ckan db init -c /etc/ckan/masaq/development.ini

You should see ``Initialising DB: SUCCESS``.

.. tip::

    If the command prompts for a password it's likely you haven't set the 
    ``sqlalchemy.url`` option in your CKAN configuration file properly.
    See `4. Create a CKAN config file`_.


7. Set up the DataStore
~~~~~~~~~~~~~~~~~~~~~~~

.. note ::
  Setting up the DataStore is optional. However, if you do skip this step,
  the :doc:`DataStore features<datastore>` will not be available and the
  DataStore tests will fail.

Follow the instructions in :doc:`datastore-setup` to create the required
databases and users, set the right permissions and set the appropriate values
in your CKAN config file.


8. Create the data and sstore directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the ``data`` and ``sstore`` directories, in the same directory that
contains your CKAN config file::

    mkdir /etc/ckan/masaq/data /etc/ckan/masaq/sstore

The location of the ``sstore`` directory, which CKAN uses as its Repoze.who
OpenID session directory, is specified by the ``store_file_path`` setting in
the ``who.ini`` file.

The location of the ``data`` directory, which CKAN uses as its Pylons cache, is
is specified by the ``cache_dir`` setting in your CKAN config file.


9. Link to who.ini
~~~~~~~~~~~~~~~~~~

``who.ini`` (the Repoze.who configuration file) needs to be accessible in the
same directory as your CKAN config file, so create a symlink to it::

    ln -s /usr/lib/ckan/masaq/src/ckan/who.ini /etc/ckan/masaq/who.ini

10. Run CKAN in the development web server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the Paste development server to serve CKAN from the command-line.
This is a simple and lightweight way to serve CKAN that is useful for
development and testing. For production it's better to serve CKAN using
Apache or nginx (see :doc:`post-installation`).

With your virtualenv activated, run this command from the ``~/pyenv/src/ckan``
directory::

    cd /usr/lib/ckan/masaq/src/ckan
    paster serve /etc/ckan/masaq/development.ini

Open http://127.0.0.1:5000/ in your web browser, and you should see the CKAN
front page.


11. Run the CKAN Tests
~~~~~~~~~~~~~~~~~~~~~~

Now that you've installed CKAN, you should run CKAN's tests to make sure that
they all pass. See :doc:`test`.

12. You're done!
~~~~~~~~~~~~~~~~

You can now proceed to :doc:`post-installation` which covers creating a CKAN
sysadmin account and deploying CKAN with Apache.

Upgrade a source install
~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

    Before upgrading your version of CKAN you should check that any custom
    templates or extensions you're using work with the new version of CKAN. For
    example, you could install the new version of CKAN in a new virtual
    environment and use that to test your templates and extensions.

.. note::

    You should also read the `CKAN Changelog
    <https://github.com/okfn/ckan/blob/master/CHANGELOG.txt>`_ to see if there
    are any extra notes to be aware of when upgrading to the new version.


1. Activate your virtualenv and switch to the ckan source directory, e.g.::

        . /usr/lib/ckan/masaq/bin/activate
        cd /usr/lib/ckan/masaq/src/ckan

2. Backup your CKAN database using the ``ckan db dump`` command, for
   example::

    paster db dump -c /etc/ckan/masaq/development.ini masaq_2013-04-24.sql

   This will create a file called ``masaq_2013-04-24.sql``, if
   something goes wrong with the CKAN upgrade you can use this file to restore
   the database to its pre-upgrade state. See :ref:`dumping and loading` for
   details of the `ckan db dump` and `ckan db load` commands.

3. Checkout the new CKAN version from git, for example::

    git fetch
    git checkout release-v2.0

   If you have any CKAN extensions installed from source, you may need to
   checkout newer versions of the extensions at this point as well. Refer to
   the documentation for each extension.

4. Update CKAN's dependencies::

     pip install --upgrade -r pip-requirements.txt

5. If you are upgrading to a new major version of CKAN (for example if you are
   upgrading to CKAN 2.0, 2.1 etc.), then you need to update your Solr schema
   symlink.

   When :ref:`setting up solr` you created a symlink
   ``/etc/solr/conf/schema.xml`` linking to a CKAN Solr schema file such as
   ``/usr/lib/ckan/masaq/src/ckan/ckan/config/solr/schema-2.0.xml``.
   This symlink should be updated to point to the latest schema file in
   ``ckan/ckan/config/solr/``, if it doesn't already.

   For example, to update the symlink::

     sudo rm /etc/solr/conf/schema.xml
     sudo ln -s /usr/lib/ckan/masaq/src/ckan/ckan/config/solr/schema-2.1.xml /etc/solr/conf/schema.xml

6. If you are upgrading to a new major version of CKAN (for example if you
   are upgrading to CKAN 2.0, 2.1 etc.), update your CKAN database's schema
   using the ``ckan db upgrade`` command.

   .. warning ::

     To avoid problems during the database upgrade, comment out any plugins
     that you have enabled in your ini file. You can uncomment them again when
     the upgrade finishes.

   For example::

    paster db upgrade -c /etc/ckan/masaq/development.ini

   See :ref:`upgrade migration` for details of the ``ckan db upgrade``
   command.

7. Rebuild your search index by running the ``ckan search-index rebuild``
   command::

    paster search-index rebuild -r -c /etc/ckan/masaq/development.ini

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

8. Finally, restart your web server. For example if you have deployed CKAN
   using the Apache web server on Ubuntu linux, run this command::

    sudo service apache2 restart

9. You're done! You should now be able to visit your CKAN website in your web
   browser and see that it's running the new version of CKAN.
