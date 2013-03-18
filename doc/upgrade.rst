=============================
Upgrading a CKAN installation
=============================

This section describes how to:

- `Upgrade a package install`_
- `Upgrade a source install`_

The overall process is the following:

1. Backup CKAN
2. Upgrade CKAN
3. Update Solr
4. Upgrade the database
5. Rebuild search engine
6. Restart Apache

For support during your upgrade, please contact `the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.

Upgrade a source install
========================

Before upgrading your version of CKAN you should check that any custom
templates or extensions you're using work with the new version of CKAN. For
example, you could install the new version of CKAN in a new virtual environment
and use that to test your templates and extensions.

You should also read the `CKAN Changelog <https://github.com/okfn/ckan/blob/master/CHANGELOG.txt>`_
to see if there are any extra notes to be aware of when upgrading to the new
version.

.. note::

    If you installed CKAN from source, you will need to activate the virtualenv and switch to the ckan source directory.
    In this case, you don't need to specifiy the `--plugin` or `--config` parameters when executing the paster commands, e.g.::

        (pyenv):~/pyenv/src/ckan$ paster user list
    
    Activate your virtualenv and change into the appropriate kcan directory, e.g.::
    
    	. ~/pyenv/bin/activate
    	cd ~/pyenv/src/ckan

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