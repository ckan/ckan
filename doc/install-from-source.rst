=============================
Option 2: Install from Source
=============================

This section describes how to install CKAN from source. Although
:doc:`install-from-package` is simpler, it requires Ubuntu 10.04. Installing
CKAN from source works with Ubuntu 10.04, with other versions of Ubuntu (e.g.
12.04) and with other operating systems (e.g. RedHat, Fedora, CentOS, OS X). If
you install CKAN from source on your own operating system, please share your
experiences on our wiki: http://wiki.ckan.org/Install

From source is also the right installation method for developers who want to
work on CKAN.

If you run into problems, see :doc:`common-error-messages` or contact `the
ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.

1. Install the required packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're using a Debian-based operating system (such as Ubuntu) install the
required packages with this command::

    sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core solr-jetty openjdk-6-jdk

If you're not using a Debian-based operating system, find the best way to
install the following packages on your operating system (see
http://wiki.ckan.org/Install for help):

=====================  ===============================================
Package                Description
=====================  ===============================================
Python                 `The Python programming language, v2.5-2.7 <http://www.python.org/getit/>`_
PostgreSQL             `The PostgreSQL database system <http://www.postgresql.org/download/>`_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
pip                    `A tool for installing and managing Python packages <http://www.pip-installer.org>`_
virtualenv             `The virtual Python environment builder <http://pypi.python.org/pypi/virtualenv>`_
Git                    `A distributed version control system <http://book.git-scm.com/2_installing_git.html>`_
Apache Solr                   `A search platform <http://lucene.apache.org/solr>`_
Jetty                  `An HTTP server <http://jetty.codehaus.org/jetty/>`_ (used for Solr)
OpenJDK 6 JDK          `The Java Development Kit <http://openjdk.java.net/install/>`_
=====================  ===============================================


2. Install CKAN into a Python virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

a. Create a Python virtual environment (virtualenv) to install CKAN into (in
   this example we create a virtualenv called ``pyenv`` in our home
   directory), and activate it::

       virtualenv --no-site-packages ~/pyenv
       . ~/pyenv/bin/activate

b. Install the CKAN source code into your virtualenv. To install the latest
   development version of CKAN (the most recent commit on the master branch of
   the CKAN git repository), run::

       pip install -e 'git+https://github.com/okfn/ckan.git#egg=ckan'

   Alternatively, to install a specific version such as CKAN 1.7.1 run::

       pip install -e 'git+https://github.com/okfn/ckan.git@ckan-1.7.1#egg=ckan'

c. Install the Python modules that CKAN requires into your virtualenv::

       pip install -r ~/pyenv/src/ckan/pip-requirements.txt

3. Setup a PostgreSQL database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List existing databases::

    sudo -u postgres psql -l

Check that the encoding of databases is 'UTF8', if not internationalisation may
be a problem. Since changing the encoding of PostgreSQL may mean deleting
existing databases, it is suggested that this is fixed before continuing with
the CKAN install.

Next you'll need to create a database user if one doesn't already exist.

.. tip ::

    If you choose a database name, user or password which are different from
    the example values suggested below then you'll need to change the
    sqlalchemy.url value accordingly in the CKAN configuration file that you'll
    create in the next step.

Create a user called ``ckanuser``, and enter ``pass`` for the password when
prompted::

    sudo -u postgres createuser -S -D -R -P ckanuser

Create the database (owned by ``ckanuser``), which we'll call ``ckantest``::

    sudo -u postgres createdb -O ckanuser ckantest

4. Create a CKAN config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With your virtualenv activated, change to the ckan directory and create a CKAN
config file::

    cd ~/pyenv/src/ckan
    paster make-config ckan development.ini

.. tip ::

    If you used a different database name or password when creating the database in
    step 6 you'll need to now edit ``development.ini`` and change the
    ``sqlalchemy.url`` line, filling in the database name, user and password you
    used::

        sqlalchemy.url = postgresql://ckanuser:pass@localhost/ckantest

    If you're using a remote host with password authentication rather than SSL
    authentication, use::

        sqlalchemy.url = postgresql://<user>:<password>@<remotehost>/ckan?sslmode=disable

.. tip ::

  Legacy installs of CKAN may have the config file in the pyenv directory, e.g.
  ``pyenv/ckan.net.ini``. This is fine but CKAN probably won't be able to find
  your ``who.ini`` file. To fix this edit ``pyenv/ckan.net.ini``, search for
  the line ``who.config_file = %(here)s/who.ini`` and change it to
  ``who.config_file = who.ini``.


5. Setup Solr
~~~~~~~~~~~~~

Follow the instructions in :ref:`solr-single` or :ref:`solr-multi-core` to
setup Solr, set appropriate values for the ``ckan.site_id`` and ``solr_url``
config variables in your CKAN config file:

::

       ckan.site_id=my_ckan_instance
       solr_url=http://127.0.0.1:8983/solr

6. Create database tables
~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have a configuration file that has the correct settings for your
database, you'll need to create the tables. Make sure you are still in an
activated environment with ``(pyenv)`` at the front of the command prompt and
then from the ``~/pyenv/src/ckan`` directory run this command::

    paster --plugin=ckan db init

You should see ``Initialising DB: SUCCESS``.

.. tip ::

    If the command prompts for a password it is likely you haven't set up the
    database configuration correctly in step 6.

.. tip ::

    If your config file is not called ``development.ini`` you must give the
    ``--config`` option, for example with a config file called
    ``test.ckan.net.ini`` you would use::

        paster --plugin=ckan db init --config=test.ckan.net.ini

7. Create the data and sstore directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the ``data`` and ``sstore`` directories, in the same directory that
contains your CKAN config file (e.g. ``~/pyenv/src/ckan``)::

    mkdir data sstore

The location of the ``data`` directory, which CKAN uses as its Pylons cache, is
is specified by the ``cache_dir`` setting in your CKAN config file.

The location of the ``sstore`` directory, which CKAN uses as its Repoze.who
OpenID session directory, is specified by the ``store_file_path`` setting in
the ``who.ini`` file.

8. Link to who.ini
~~~~~~~~~~~~~~~~~~

``who.ini`` (the Repoze.who configuration file) needs to be accessible in the
same directory as your CKAN config file. So if your config file is not in
``~/pyenv/src/ckan``, then cd to the directory with your config file and create a
symbolic link to ``who.ini``. e.g.::

    ln -s ~/pyenv/src/ckan/who.ini

9. Run CKAN in the development web server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the Paste development server to serve CKAN from the command-line.
This is a simple and lightweight way to serve CKAN that is useful for
development and testing. For production it's better to serve CKAN using
Apache or nginx (see :doc:`post-installation`).

With your virtualenv activated, run this command from the ``~/pyenv/src/ckan``
directory::

    paster serve development.ini

Open http://127.0.0.1:5000/ in your web browser, and you should see the CKAN
front page.

.. tip:: If you installed CKAN on a remote machine then you'll need to run
 the web browser on that same machine. For example run the textual web browser
 `w3m` in a separate ssh session to the one running `paster serve`.

10. Run the CKAN Tests
~~~~~~~~~~~~~~~~~~~~~~

Now that you've installed CKAN, you should run CKAN's tests to make sure that
they all pass. See :doc:`test`.

11. You're done!
~~~~~~~~~~~~~~~~

You can now proceed to :doc:`post-installation` which covers creating a CKAN
sysadmin account and deploying CKAN with Apache.

Upgrading a source install
~~~~~~~~~~~~~~~~~~~~~~~~~~

Before upgrading your version of CKAN you should check that any custom
templates or extensions you're using work with the new version of CKAN. For
example, you could install the new version of CKAN in a new virtual environment
and use that to test your templates and extensions.

You should also read the `CKAN Changelog <https://github.com/okfn/ckan/blob/master/CHANGELOG.txt>`_
to see if there are any extra notes to be aware of when upgrading to the new
version.

1. Backup your CKAN database using the ``ckan db dump`` command, for example::

    paster --plugin=ckan db dump --config=/path/to/your/ckan.ini my_ckan_database.pg_dump

   This will create a file called ``my_ckan_database.pg_dump``, if something
   goes wrong with the CKAN upgrade you can use this file to restore the
   database to its pre-upgrade state. See :ref:`dumping and loading` for
   details of the `ckan db dump` and `ckan db load` commands.

2. Checkout the new CKAN version from git, for example::

    cd pyenv/src/ckan
    git fetch
    git checkout release-v1.8.1

   If you have any CKAN extensions installed from source, you may need to
   checkout newer versions of the extensions at this point as well. Refer to
   the documentation for each extension.

3. Update CKAN's dependencies. Make sure that your CKAN virtual environment
   is active, then run this command::

     pip install --upgrade -r /path/to/your/pyenv/ckan/ckan/pip-requirements.txt

4. If you are upgrading to a new major version of CKAN (for example if you are
   upgrading to CKAN 1.7, 1.8 or 1.9, etc.), update your CKAN database's schema
   using the ``ckan db upgrade`` command.

    .. warning ::

        To avoid problems during the database upgrade, comment out any
        plugins that you have enabled on your ini file. You can uncomment
        them back when the upgrade finishes.

   For example::

    paster --plugin=ckan db upgrade --config=/path/to/your/ckan.ini

   If you are just upgrading to a minor version of CKAN (for example upgrading
   from version 1.8 to 1.8.1) then it should not be necessary to upgrade your
   database.

   See :ref:`upgrade migration` for details of the ``ckan db upgrade`` command.

5. If CKAN's Solr schema version has changed between the CKAN versions you're
   upgrading from and to, then you need to update your solr schema symlink
   (Check the CHANGELOG to see if it necessary to update the schema, otherwise
   you can skip this step).

   When :ref:`setting up solr` you created a symlink
   ``/etc/solr/conf/schema.xml`` linking to a CKAN Solr schema file such as
   ``/path/to/your/pyenv/ckan/ckan/config/solr/schema-1.4.xml``. This symlink
   should be updated to point to the latest schema file in
   ``/path/to/your/pyenv/ckan/ckan/config/solr/``, if it doesn't already.

   After updating the symlink, you must rebuild your search index by running
   the ``ckan search-index rebuild`` command, for example::

    paster --plugin=ckan search-index rebuild --config=/path/to/your/ckan.ini

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

6. Finally, restart your web server. For example if you have deployed CKAN
   using the Apache web server on Ubuntu linux, run this command::

    sudo service apache2 restart

7. You're done! You should now be able to visit your CKAN website in your web
   browser and see that it's now running the new version of CKAN.
