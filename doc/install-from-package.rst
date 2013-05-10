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

    sudo apt-get install nginx apache2 libapache2-mod-wsgi libpq5

#. Download the CKAN package::

    wget http://packages.ckan.org/python-ckan-2.0_amd64.deb

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

3. You're done!
---------------

Open http://localhost:5000 in your web browser. You should see the CKAN front
page, which will look something like this:

.. image :: images/9.png
   :width: 807px

|
You can now proceed to :doc:`post-installation`.


.. _upgrading:

Upgrading a Package Install
---------------------------

.. note::

   The CKAN 2.0 package only works on Ubuntu 12.04 64-bit.

.. versionchanged: 1.7

   Before CKAN 1.7, it was not necessary to uninstall and reinstall the CKAN
   package when upgrading between major versions.

.. note::

   **Major versions** of CKAN, such as 2.0, 1.8 and 1.7, can introduce
   backwards-incompatible changes, and changes to CKAN's database and |solr|
   schemas. **Minor versions**, such as 1.7.1 or 1.7.2, contain only bug
   fixes, non-breaking optimizations, and new translations. The procedure for
   upgrading a CKAN package install is different depending on whether you're
   upgrading to a new major version, or just upgrading to a new minor version
   within the same major version.

If you're upgrading to a new major version of CKAN, follow the instructions in
`Upgrading to a new major version`_ below. If you're only upgrading to a new
minor version, follow `Upgrading to a new minor version`_ instead.

Upgrading to a new major version
********************************

.. caution ::

   Always make a backup first and be prepared to start again with a fresh
   install of the newer version of CKAN.

#. First, uninstall the old CKAN package (this won't remove your data or
   configuration)::

    sudo apt-get autoremove ckan

   Then, follow the instructions in :ref:`run-package-installer` to install
   the new CKAN package.

#. Move your ``production.ini`` file. The location of the ``production.ini``
   file has changed in 2.0, you'll need to move your ``production.ini`` file to
   |production.ini|.

#. Upgrade your Solr schema.

   Configure ``ckan.site_url`` or ``ckan.site_id`` in |production.ini| for |solr| search-index rebuild to work. eg:

   ::

       ckan.site_id = yoursite.ckan.org

   The site_id must be unique so the domain name of the CKAN instance is a good choice.

   Install the new schema:

   ::

       sudo rm /usr/share/solr/conf/schema.xml
       sudo ln -s /usr/lib/ckan/default/src/ckan/ckan/config/solr/schema-2.0.xml /usr/share/solr/conf/schema.xml

#. Upgrade your database::

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


Upgrading to a new minor version
********************************

If you only want to upgrade to a new minor version (e.g. upgrade to 1.7.1 to
1.7, or to 1.7.2 from 1.7.1), then you only need to update the `python-ckan`
package to get the latest changes::

    sudo apt-get install python-ckan

.. caution::

    This assumes that you already have installed CKAN via package install. If
    not, do not install this single package, follow the instructions on :ref:`run-package-installer`

After upgrading the package, you need to restart Apache for the changes to take
effect::

   sudo service apache2 restart
