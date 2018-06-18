.. include:: /_substitutions.rst

===========================
Installing CKAN from source
===========================

This section describes how to install CKAN from source. Although
:doc:`install-from-package` is simpler, it requires Ubuntu 16.04 64-bit or
Ubuntu 14.04 64-bit. Installing CKAN from source works with other versions of
Ubuntu and with other operating systems (e.g. RedHat, Fedora, CentOS, OS X). If
you install CKAN from source on your own operating system, please share your
experiences on our
`How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`_
wiki page.

From source is also the right installation method for developers who want to
work on CKAN.

--------------------------------
1. Install the required packages
--------------------------------

If you're using a Debian-based operating system (such as Ubuntu) install the
required packages with this command for Ubuntu 16.04::

    sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core solr-jetty openjdk-8-jdk redis-server

or for Ubuntu 14.04::

    sudo apt-get install python-dev postgresql libpq-dev python-pip python-virtualenv git-core solr-jetty openjdk-6-jdk redis-server

If you're not using a Debian-based operating system, find the best way to
install the following packages on your operating system (see
our `How to Install CKAN <https://github.com/ckan/ckan/wiki/How-to-Install-CKAN>`_
wiki page for help):

=====================  ===============================================
Package                Description
=====================  ===============================================
Python                 `The Python programming language, v2.7 <http://www.python.org/getit/>`_
|postgres|             `The PostgreSQL database system, v9.3 or newer <http://www.postgresql.org/download/>`_
libpq                  `The C programmer's interface to PostgreSQL <http://www.postgresql.org/docs/8.1/static/libpq.html>`_
pip                    `A tool for installing and managing Python packages <http://www.pip-installer.org>`_
virtualenv             `The virtual Python environment builder <http://www.virtualenv.org>`_
Git                    `A distributed version control system <http://book.git-scm.com/2_installing_git.html>`_
Apache Solr            `A search platform <http://lucene.apache.org/solr>`_
Jetty                  `An HTTP server <http://www.eclipse.org/jetty/>`_ (used for Solr).
OpenJDK JDK            `The Java Development Kit <http://openjdk.java.net/install/>`_ (used by Jetty)
Redis                  `An in-memory data structure store <http://redis.io/>`_
=====================  ===============================================


.. _install-ckan-in-virtualenv:

-------------------------------------------------
2. Install CKAN into a Python virtual environment
-------------------------------------------------

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

b. Install the recommended ``setuptools`` version:

   .. parsed-literal::

       pip install setuptools==\ |min_setuptools_version|

c. Install the CKAN source code into your virtualenv.

   To install the latest stable release of CKAN (CKAN |latest_release_version|),
   run:

   .. parsed-literal::

      pip install -e 'git+\ |git_url|\@\ |latest_release_tag|\#egg=ckan'

   If you're installing CKAN for development, you may want to install the
   latest development version (the most recent commit on the master branch of
   the CKAN git repository). In that case, run this command instead:

   .. parsed-literal::

       pip install -e 'git+\ |git_url|\#egg=ckan'

   .. warning::

      The development version may contain bugs and should not be used for
      production websites! Only install this version if you're doing CKAN
      development.

d. Install the Python modules that CKAN requires into your virtualenv:

   .. parsed-literal::

       pip install -r |virtualenv|/src/ckan/requirements.txt

e. Deactivate and reactivate your virtualenv, to make sure you're using the
   virtualenv's copies of commands like ``paster`` rather than any system-wide
   installed copies:

   .. parsed-literal::

        deactivate
        |activate|

.. _postgres-setup:

------------------------------
3. Setup a PostgreSQL database
------------------------------

.. include:: postgres.rst

----------------------------
4. Create a CKAN config file
----------------------------

Create a directory to contain the site's config files:

.. parsed-literal::

    sudo mkdir -p |config_dir|
    sudo chown -R \`whoami\` |config_parent_dir|/
    sudo chown -R \`whoami\` ~/ckan/etc

Create the CKAN config file:

.. parsed-literal::

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

site_url
  Provide the site's URL (used when putting links to the site into the
  FileStore, notification emails etc). For example::

    ckan.site_url = http://demo.ckan.org

  Do not add a trailing slash to the URL.

.. _setting up solr:

-------------
5. Setup Solr
-------------

.. include:: solr.rst


.. _postgres-init:

----------------------
6. Link to ``who.ini``
----------------------

``who.ini`` (the Repoze.who configuration file) needs to be accessible in the
same directory as your CKAN config file, so create a symlink to it:

.. parsed-literal::

    ln -s |virtualenv|/src/ckan/who.ini |config_dir|/who.ini

-------------------------
7. Create database tables
-------------------------

Now that you have a configuration file that has the correct settings for your
database, you can :ref:`create the database tables <db init>`:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    paster db init -c |development.ini|

You should see ``Initialising DB: SUCCESS``.

.. tip::

    If the command prompts for a password it is likely you haven't set up the
    ``sqlalchemy.url`` option in your CKAN configuration file properly.
    See `4. Create a CKAN config file`_.

-----------------------
8. Set up the DataStore
-----------------------

.. note ::
  Setting up the DataStore is optional. However, if you do skip this step,
  the :doc:`DataStore features </maintaining/datastore>` will not be available
  and the DataStore tests will fail.

Follow the instructions in :doc:`/maintaining/datastore` to create the required
databases and users, set the right permissions and set the appropriate values
in your CKAN config file.

---------------
9. You're done!
---------------

You can now use the Paste development server to serve CKAN from the
command-line.  This is a simple and lightweight way to serve CKAN that is
useful for development and testing:

.. parsed-literal::

    cd |virtualenv|/src/ckan
    paster serve |development.ini|

Open http://127.0.0.1:5000/ in a web browser, and you should see the CKAN front
page.

Now that you've installed CKAN, you should:

* Run CKAN's tests to make sure that everything's working, see :doc:`/contributing/test`.

* If you want to use your CKAN site as a production site, not just for testing
  or development purposes, then deploy CKAN using a production web server such
  as Apache or Nginx. See :doc:`deployment`.

* Begin using and customizing your site, see :doc:`/maintaining/getting-started`.

.. note:: The default authorization settings on a new install are deliberately
    restrictive. Regular users won't be able to create datasets or organizations.
    You should check the :doc:`/maintaining/authorization` documentation, configure CKAN accordingly
    and grant other users the relevant permissions using the :ref:`sysadmin account <create-admin-user>`.

------------------------------
Source install troubleshooting
------------------------------

.. _solr troubleshooting:

Solr setup troubleshooting
==========================

Solr requests and errors are logged in the web server log files.

* For Jetty servers, the log files are::

    /var/log/jetty/<date>.stderrout.log

* For Tomcat servers, they're::

    /var/log/tomcat6/catalina.<date>.log

Unable to find a javac compiler
-------------------------------

If when running Solr it says:

 Unable to find a javac compiler; com.sun.tools.javac.Main is not on the classpath. Perhaps JAVA_HOME does not point to the JDK.

See the note in :ref:`setting up solr` about ``JAVA_HOME``.
Alternatively you may not have installed the JDK.
Check by seeing if ``javac`` is installed::

     which javac

If ``javac`` isn't installed, do::

     sudo apt-get install openjdk-6-jdk

and then restart Solr:

For Ubuntu 16.04::

     sudo service jetty8 restart

or for Ubuntu 14.04::

     sudo service jetty restart

AttributeError: 'module' object has no attribute 'css/main.debug.css'
---------------------------------------------------------------------

This error is likely to show up when `debug` is set to `True`. To fix this
error, install frontend dependencies. See :doc:`/contributing/frontend/index`.

After installing the dependencies, run ``bin/less`` and then start paster server
again.

If you do not want to compile CSS, you can also copy the main.css to
main.debug.css to get CKAN running::

    cp /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.css \
    /usr/lib/ckan/default/src/ckan/ckan/public/base/css/main.debug.css

JSP support not configured
--------------------------

This is seen occasionally with Jetty and Ubuntu 14.04. It requires a solr-jetty fix::

    cd /tmp
    wget https://launchpad.net/~vshn/+archive/ubuntu/solr/+files/solr-jetty-jsp-fix_1.0.2_all.deb
    sudo dpkg -i solr-jetty-jsp-fix_1.0.2_all.deb
    sudo service jetty restart
