=============================
Upgrading a CKAN installation
=============================

This section describes how to upgrade CKAN for both packages and source installations.

The overall process is the following:

=======                            ======
Package                            Source
=======                            ======
* :ref:`upgrade-ckan-package`      * :ref:`upgrade-ckan-source`
* :ref:`update-solr-package`       * :ref:`update-solr-source`
* :ref:`upgrade-database-package`  * :ref:`upgrade-database-source`
* :ref:`rebuild-search-package`    * :ref:`rebuild-search-source`
* :ref:`restart-apache-package`    * :ref:`restart-apache-source`
=======                            ======
For support during your upgrade, please contact `the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.

.. _upgrading:

Upgrading a package install
---------------------------

Starting on CKAN 1.7, the updating process is different depending on wether
the new version is a major release (e.g. 1.7, 1.8, etc) or a minor release
(e.g. 1.7.X, 1.7.Y). Major releases can introduce backwards incompatible
changes, changes on the database and the Solr schema. Each major release and
its subsequent minor versions has its own apt repository (Please note that this
was not true for 1.5 and 1.5.1 versions).

Minor versions, on the other hand contain only bug fixes, non-breaking
optimizations and new translations.

A fresh install or upgrade from another major version will install the latest minor
version.

Upgrading from another major version
************************************
If you already have a major version installed via package install and wish to upgrade, you can try the approach documented below.

.. caution ::

   Always make a backup first and be prepared to start again with a fresh install of the newer version of CKAN.

First remove the old CKAN code (it doesn't remove your data):

::

    sudo apt-get autoremove ckan

Then update the repositories (replace `MAJOR_VERSION` with a suitable value):

::

    echo "deb http://apt.ckan.org/ckan-1.MAJOR_VERSION lucid universe" | sudo tee /etc/apt/sources.list.d/ckan.list
    wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -
    sudo apt-get update

Install the new CKAN and update all the dependencies:

::

    sudo apt-get install ckan

Now you need to make some manual changes. In the following commands replace ``std`` with the name of your CKAN instance. Perform these steps for each instance you wish to upgrade.

#. Upgrade the Solr schema

    .. note ::

       This only needs to be done if the Solr schema has been updated between major releases. The CHANGELOG or the announcement
       emails will specify if this is the case.

   Configure ``ckan.site_url`` or ``ckan.site_id`` in ``/etc/ckan/std/std.ini`` for SOLR search-index rebuild to work. eg:

   ::

       ckan.site_id = yoursite.ckan.org

   The site_id must be unique so the domain name of the CKAN instance is a good choice.

   Install the new schema:

   ::

       sudo rm /usr/share/solr/conf/schema.xml
       sudo ln -s /usr/lib/pymodules/python2.6/ckan/config/solr/schema-1.4.xml /usr/share/solr/conf/schema.xml

#. Upgrade the database

   First install pastescript:

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/pip install --ignore-installed pastescript

   Then upgrade the database:

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db upgrade --config=/etc/ckan/std/std.ini

   When upgrading from CKAN 1.5 you may experience error ``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key``. In this case then you need to rename users with duplicate names, before the database upgrade will run successfully. For example::

        sudo -u ckanstd paster --plugin=pylons shell /etc/ckan/std/std.ini
        model.meta.engine.execute('SELECT name, count(name) AS NumOccurrences FROM "user" GROUP BY name HAVING(COUNT(name)>1);').fetchall()
        users = model.Session.query(model.User).filter_by(name='https://www.google.com/accounts/o8/id?id=ABCDEF').all()
        users[1].name = users[1].name[:-1]
        model.repo.commit_and_remove()

#. Rebuild the search index (this can take some time - e.g. an hour for 5000 datasets):

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan search-index rebuild --config=/etc/ckan/std/std.ini

#. Restart Apache

   ::

       sudo /etc/init.d/apache2 restart


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

   sudo /etc/init.d/apache2 restart

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