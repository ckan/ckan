Installing CKAN from Source
===========================

This section describes how to install CKAN from source. Although
:doc:`install-from-package` is simpler, it requires Ubuntu 12.04 64-bit. Installing
CKAN from source works with other versions of Ubuntu and with other operating
systems (e.g. RedHat, Fedora, CentOS, OS X). If you install CKAN from source
on your own operating system, please share your experiences on our
`How to Install CKAN <https://github.com/okfn/ckan/wiki/How-to-Install-CKAN>`_
wiki page.

From source is also the right installation method for developers who want to
work on CKAN.

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
|postgres|             `The PostgreSQL database system, v8.4 or newer <http://www.postgresql.org/download/>`_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
pip                    `A tool for installing and managing Python packages <http://www.pip-installer.org>`_
virtualenv             `The virtual Python environment builder <http://www.virtualenv.org>`_
Git                    `A distributed version control system <http://book.git-scm.com/2_installing_git.html>`_
Apache Solr                   `A search platform <http://lucene.apache.org/solr>`_
Jetty                  `An HTTP server <http://jetty.codehaus.org/jetty/>`_ (used for Solr)
OpenJDK 6 JDK          `The Java Development Kit <http://openjdk.java.net/install/>`_
=====================  ===============================================


.. _install-ckan-in-virtualenv:

2. Install CKAN into a Python virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tip::

   If you're installing CKAN for development and want it to be installed in
   your home directory, you can symlink the directories used in this
   documentation to your home directory. This way, you can copy-paste the
   example commands from this documentation without having to modify them, and
   still have CKAN installed in your home directory:

   .. parsed-literal::

     mkdir -p ~/ckan/lib
     sudo ln -s ~/ckan/lib |virtualenv_parent_dir|
     mkdir -p ~/ckan/etc
     sudo ln -s ~/ckan/etc |config_parent_dir|

a. Create a Python `virtual environment <http://www.virtualenv.org>`_
   (virtualenv) to install CKAN into, and activate it:

   .. parsed-literal::

       sudo mkdir -p |virtualenv|
       sudo chown \`whoami\` |virtualenv|
       virtualenv --no-site-packages |virtualenv|
       |activate|

.. important::

   The final command above activates your virtualenv. The virtualenv has to
   remain active for the rest of the installation and deployment process,
   or commands will fail. You can tell when the virtualenv is active because
   its name appears in front of your shell prompt, something like this::

     (default) $ _

   For example, if you logout and login again, or if you close your terminal
   window and open it again, your virtualenv will no longer be activated. You
   can always reactivate the virtualenv with this command:

   .. parsed-literal::

       |activate|

b. Install the CKAN source code into your virtualenv. To install the latest
   development version of CKAN (the most recent commit on the master branch of
   the CKAN git repository), run:

   .. parsed-literal::

       pip install -e 'git+\ |git_url|\#egg=ckan'

   Alternatively, to install a specific version such as CKAN 2.0 run:

   .. parsed-literal::

       pip install -e 'git+\ |git_url|\@ckan-2.0#egg=ckan'

c. Install the Python modules that CKAN requires into your virtualenv:

   .. parsed-literal::

       pip install -r |virtualenv|/src/ckan/requirements.txt

d. Deactivate and reactivate your virtualenv, to make sure you're using the
   virtualenv's copies of commands like ``paster`` rather than any system-wide
   installed copies:

   .. parsed-literal::

        deactivate
        |activate|

.. _postgres-setup:

3. Setup a PostgreSQL database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List existing databases::

    sudo -u postgres psql -l

Check that the encoding of databases is ``UTF8``, if not internationalisation
may be a problem. Since changing the encoding of |postgres| may mean deleting
existing databases, it is suggested that this is fixed before continuing with
the CKAN install.

Next you'll need to create a database user if one doesn't already exist.
Create a new |postgres| database user called |database_user|, and enter a
password for the user when prompted. You'll need this password later:

.. parsed-literal::

    sudo -u postgres createuser -S -D -R -P |database_user|

Create a new |postgres| database, called |database|, owned by the
database user you just created:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |database| -E utf-8


4. Create a CKAN config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a directory to contain the site's config files:

.. parsed-literal::

    sudo mkdir -p |config_dir|
    sudo chown -R \`whoami\` |config_parent_dir|/

Change to the ``ckan`` directory and create a CKAN config file:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    paster make-config ckan |development.ini|

Edit the ``development.ini`` file in a text editor, changing the following
options:

sqlalchemy.url
  This should refer to the database we created in `3. Setup a PostgreSQL
  database`_ above:

  .. parsed-literal::

    sqlalchemy.url = postgresql://|database_user|:pass@localhost/|database|

  Replace ``pass`` with the password that you created in `3. Setup a
  PostgreSQL database`_ above.

  .. tip ::

    If you're using a remote host with password authentication rather than SSL
    authentication, use:

    .. parsed-literal::

      sqlalchemy.url = postgresql://|database_user|:pass@<remotehost>/|database|?sslmode=disable

site_id
  Each CKAN site should have a unique ``site_id``, for example::

   ckan.site_id = default


5. Setup Solr
~~~~~~~~~~~~~

Follow the instructions in :ref:`solr-single` or :ref:`solr-multi-core` to
setup Solr, then change the ``solr_url`` option in your CKAN config file to
point to your Solr server, for example::

       solr_url=http://127.0.0.1:8983/solr

.. toctree::
   :hidden:

   solr-setup

.. _postgres-init:

6. Create database tables
~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have a configuration file that has the correct settings for your
database, you can create the database tables:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    paster db init -c |development.ini|

You should see ``Initialising DB: SUCCESS``.

.. tip::

    If the command prompts for a password it is likely you haven't set up the
    ``sqlalchemy.url`` option in your CKAN configuration file properly.
    See `4. Create a CKAN config file`_.

7. Set up the DataStore
~~~~~~~~~~~~~~~~~~~~~~~

.. note ::
  Setting up the DataStore is optional. However, if you do skip this step,
  the :doc:`DataStore features<datastore>` will not be available and the
  DataStore tests will fail.

Follow the instructions in :doc:`datastore` to create the required
databases and users, set the right permissions and set the appropriate values
in your CKAN config file.

8. Link to ``who.ini``
~~~~~~~~~~~~~~~~~~~~~~

``who.ini`` (the Repoze.who configuration file) needs to be accessible in the
same directory as your CKAN config file, so create a symlink to it:

.. parsed-literal::

    ln -s |virtualenv|/src/ckan/who.ini |config_dir|/who.ini

9. You're done!
~~~~~~~~~~~~~~~

You can now use the Paste development server to serve CKAN from the
command-line.  This is a simple and lightweight way to serve CKAN that is
useful for development and testing:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    paster serve |development.ini|

Open http://127.0.0.1:5000/ in a web browser, and you should see the CKAN front
page.

Now that you've installed CKAN, you should:

* Run CKAN's tests to make sure that everything's working, see :doc:`/test`.

* If you want to use your CKAN site as a production site, not just for testing
  or development purposes, then deploy CKAN using a production web server such
  as Apache or Nginx. See :doc:`deployment`.

* Begin using and customizing your site, see :doc:`/getting-started`.
