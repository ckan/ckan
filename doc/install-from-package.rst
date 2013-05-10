==============================
Option 1: Package Installation
==============================

This section describes how to install CKAN from packages. This is the
recommended and the easiest way to install CKAN, but it requires **Ubuntu 12.04
64-bit**. If you're not using Ubuntu 12.04 64-bit, or if you're installing CKAN
for development, you should follow :doc:`install-from-source` instead.

If you run into problems, see :doc:`common-error-messages`.

.. _run-package-installer:

1. Install the CKAN Package
---------------------------

On your Ubuntu 12.04 system, open a terminal and run these commands to install
CKAN:

#. Update Ubuntu's package index::

    sudo apt-get update

#. Install the Ubuntu packages that CKAN requires::

    sudo apt-get install -y nginx apache2 libapache2-mod-wsgi libpq5

#. Download the CKAN package::

    wget http://packages.ckan.org/python-ckan-2.0_amd64.deb

   .. note:: If ``wget`` is not present, you can install it
       via::

        sudo apt-get install wget

#. Install the CKAN package::

    sudo dpkg -i python-ckan-2.0_amd64.deb

.. note:: If you get the following error it means that for some reason the
 Apache WSGI module was not enabled::

    Syntax error on line 1 of /etc/apache2/sites-enabled/ckan_default:
    Invalid command 'WSGISocketPrefix', perhaps misspelled or defined by a module not included in the server configuration
    Action 'configtest' failed.
    The Apache error log may have more information.
       ...fail!

 You can enable it by running these commands in a terminal::

    sudo a2enmod wsgi
    sudo service apache2 restart


2. Install PostgreSQL and Solr
------------------------------

.. tip::

   You can install |postgres|, |solr| and CKAN on different servers. Just
   change the :ref:`sqlalchemy.url` and :ref:`solr_url` settings in your
   |production.ini| file to reference your |postgres| and |solr| servers.

#. Install |postgres| and |solr|, run this command in a terminal::

    sudo apt-get install -y postgresql solr-jetty

   The install will whirr away, then towards the end you'll see this::

     * Not starting jetty - edit /etc/default/jetty and change NO_START to be 0 (or comment it out).

#. Follow the instructions in :ref:`solr-single` or :ref:`solr-multi-core` to
   setup |solr|.

#. Follow the instructions in :ref:`postgres-setup` to setup |postgres|,
   then edit the :ref:`sqlalchemy.url` option in your |production.ini| file and
   set the correct password, database and database user.

#. Initialize your CKAN database by running this command in a terminal::

    sudo ckan db init

#. Optionally, setup the :doc:`DataStore <datastore>` by following the
   instructions in :doc:`datastore-setup`.

#. Also optionally, you can enable file uploads by following the
   instructions in :doc:`filestore`.

3. You're done!
---------------

Open http://localhost:5000 in your web browser. You should see the CKAN front
page, which will look something like this:

.. image :: images/9.png
   :width: 807px

|
You can now proceed to :doc:`post-installation`.


.. _upgrading-to-2.0:

Upgrading to CKAN 2.0
---------------------

.. note::

   If you are upgrading to a 1.X version of CKAN check the
   `documentation <http://docs.ckan.org/en/ckan-1.8/install-from-package.html#upgrading-a-package-install>`_
   relevant to the old packaging system.

CKAN 2.0 packages require Ubuntu 12.04 64-bit and install the files
in different locations from the 1.X ones. These changes have been made to 
simplify the installation and packaging process and bring source and package
installations closer, but unfortunately this means that there is not a direct
upgrade path from 1.X to 2.0.

The upgrade process will roughly involve the following steps:

.. warning::

    Always make a backup of the database and any configuration or custom
    extensions that you have.


* Create a dump of your 1.X database::

    sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db dump db-1.x.dump --config=/etc/ckan/std/std.ini

* Install CKAN 2.0, either from a :doc:`source install <install-from-source>`
  or a :doc:`package install <install-from-package>`, but don't initialize a 
  database (don't run the ``db init`` command).

* Load the old database dump. This will also try to upgrade the database to
  the latest version and rebuild the search index afterwards::

    sudo ckan db load db-1.x.dump

CKAN 2.0 introduces significant backwards incompatible changes with previous
versions, so if you are using custom extensions you will need to update them.
Main changes include:

* The :doc:`toolkit` allows safer interation with CKAN core, as the methods
  provided will work across different CKAN versions.

* The front-end templates have been rewritten to Jinja2, so any custom ones
  will need to be adapted. See :doc:`theming` for details.

* CKAN 2.0 introduces a new form of :doc:`authorization` based on
  organizations. Have a look at the documentation and decide on the best way
  to migrate and configure the new instance.

Have a look at the :doc:`CHANGELOG` for a more comprehensive list of changes.

We recommend enabling the different extensions used one by one to identify
potential problems and things that need updating.
