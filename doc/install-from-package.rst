==============================
Option 1: Package Installation
==============================

This section describes how to install CKAN from packages. This is the recommended and the easiest way to install CKAN.

The overall process is the following:

* :ref:`prepare-your-system`
* :ref:`run-package-installer`
* :ref:`setup-postgres-solr`
* :ref:`upgrading`

.. note:: We recommend you use package installation unless you are a core CKAN developer or have no access to Ubuntu 12.04, in which case you should use :doc:`install-from-source`.

.. _prepare-your-system:

Prepare your system
-------------------

Package install requires you to use **Ubuntu 12.04 64-bit**: either locally,
through a virtual machine (like `VirtualBox <https://www.virtualbox.org/>`_) or
a cloud service like Amazon EC2, Rackspace, Azure, etc.

.. _run-package-installer:

Run the Package Installer
-------------------------

On your Ubuntu 12.04 system, open a terminal and run these commands to prepare your system::

    sudo apt-get update
    wget http://packages.ckan.org/python-ckan-2.0_amd64.deb

Install the following requirements::

    sudo apt-get install nginx apache2 libapache2-mod-wsgi libpq5

Now you are ready to install::

    sudo dpkg -i python-ckan-2.0_amd64.deb

.. note:: If you get the following error it means that for some reason the
 Apache WSGI module was not enabled::

    Syntax error on line 1 of /etc/apache2/sites-enabled/ckan_default:
    Invalid command 'WSGISocketPrefix', perhaps misspelled or defined by a module not included in the server configuration
    Action 'configtest' failed.
    The Apache error log may have more information.
       ...fail!

 You can enable it running::

    sudo a2enmod wsgi
    sudo service apache2 restart


.. _setup-postgres-solr:

Install PostgreSQL and Solr
---------------------------

If you already have PostgreSQL or Solr instances that you want to use set
up on the same or a different server you don't need to install them locally.
You will only need to update the :ref:`sqlalchemy.url`
    and :ref:`solr_url` options on the `/etc/ckan/default/production.ini` file
to match your settings.

The most simple case though is to run CKAN, PostgreSQL and Solr on the same
server. To install PostgreSQL and Solr run::

    sudo apt-get install -y postgresql solr-jetty

The install will whirr away, then towards the end you'll see this::

     * Not starting jetty - edit /etc/default/jetty and change NO_START to be 0 (or comment it out).

Follow the instructions in :ref:`solr-single` or :ref:`solr-multi-core` to
setup Solr and :ref:`postgres-setup` to setup and PostgreSQL for ckan.

Once you have set up PostgresSQL, edit the :ref:`sqlalchemy.url`
option on the `/etc/ckan/default/production.ini` file with the password that
you defined (or the database and user name if you didn't use the default ones).

To initialize the database, run the following::

    sudo ckan db init

You can optionally set up the :doc:`DataStore features<datastore>`. Follow the
instructions in :doc:`datastore-setup` to create the required databases and
users, set the right permissions and set the appropriate values in your CKAN
config file.

Visit your CKAN instance at `http://localhost:5000`. The welcome screen will
look something like this:

.. image :: images/9.png
  :width: 807px

|
Now you should be up and running. Don't forget you there is the a help page for
dealing with :doc:`common-error-messages`.
You can now proceed to :doc:`post-installation`.

.. _upgrading:

Upgrading a package install
---------------------------

The CKAN 2.0 package is incompatible with the earlier packages and will only
work on Ubuntu 12.04 64-bit.

Starting on CKAN 1.7, the updating process is different depending on whether
the new version is a major release (e.g. 1.7, 1.8, etc) or a minor release
(e.g. 1.7.X, 1.7.Y). Major releases can introduce backwards incompatible changes,
changes on the database and the Solr schema. Each major release until 1.8 and
its subsequent minor versions has its own apt repository (Please note that this
was not true for 1.5 and 1.5.1 versions).

Minor versions, on the other hand contain only bug fixes, non-breaking
optimizations and new translations.

A fresh install or upgrade from another major version will install the latest
minor version.

Upgrading from another major version
************************************
If you already have a major version installed via pacakge install and wish to
upgrade to 2.0, you need to uninstall ckan and reinstall.

.. caution ::

   Always make a backup first and be prepared to start again with a fresh install of the newer version of CKAN.

First remove the old CKAN code (it doesn't remove your data):

::

    sudo apt-get autoremove ckan

Then follow the instructions in :ref:`run-package-installer`. Please note the
location of ``production.ini`` has changed in 2.0 and you'll need to move your
configuration to ``/etc/ckan/default``.

#. Upgrade the Solr schema

    .. note ::

       This only needs to be done if the Solr schema has been updated between major releases. The CHANGELOG or the announcement
       emails will specify if this is the case.

   Configure ``ckan.site_url`` or ``ckan.site_id`` in ``/etc/ckan/default/production.ini`` for SOLR search-index rebuild to work. eg:

   ::

       ckan.site_id = yoursite.ckan.org

   The site_id must be unique so the domain name of the CKAN instance is a good choice.

   Install the new schema:

   ::

       sudo rm /usr/share/solr/conf/schema.xml
       sudo ln -s /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema-2.0.xml /usr/share/solr/conf/schema.xml

#. Upgrade the database

   ::

       sudo -u ckan db upgrade

   When upgrading from CKAN 1.5 you may experience error ``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key``. In this case then you need to rename users with duplicate names, before the database upgrade will run successfully. For example::

        sudo -u ckanstd paster --plugin=pylons shell /etc/ckan/std/std.ini
        model.meta.engine.execute('SELECT name, count(name) AS NumOccurrences FROM "user" GROUP BY name HAVING(COUNT(name)>1);').fetchall()
        users = model.Session.query(model.User).filter_by(name='https://www.google.com/accounts/o8/id?id=ABCDEF').all()
        users[1].name = users[1].name[:-1]
        model.repo.commit_and_remove()

#. Rebuild the search index (this can take some time - e.g. an hour for 5000 datasets):

   ::

       sudo -u ckan search-index rebuild

#. Restart Apache

   ::

       sudo service apache2 restart


Upgrading from the same major version
*************************************

If you want to update to a new minor version of a major release (e.g. upgrade
to 1.7.1 to 1.7, or to 1.7.2 from 1.7.1), then you only need to update the
`python-ckan` package to get the latest changes::

    sudo apt-get install python-ckan

.. caution::

    This assumes that you already have installed CKAN via package install. If
    not, do not install this single package, follow the instructions on :ref:`run-package-installer`

After upgrading the package, you need to restart Apache for the effects to take
place::

   sudo service apache2 restart




