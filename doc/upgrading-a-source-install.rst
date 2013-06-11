Upgrading a Source Install
==========================

.. note::

    Before upgrading your version of CKAN you should check that any custom
    templates or extensions you're using work with the new version of CKAN. For
    example, you could install the new version of CKAN in a new virtual
    environment and use that to test your templates and extensions.

.. note::

    You should also read the `CKAN Changelog
    <https://github.com/okfn/ckan/blob/master/CHANGELOG.txt>`_ to see if there
    are any extra notes to be aware of when upgrading to the new version.

.. todo::

   Run python setup.py develop!


1. Activate your virtualenv and switch to the ckan source directory, e.g.:

   .. parsed-literal::

    |activate|
    cd |virtualenv|/src/ckan

2. Backup your CKAN database using the ``db dump`` command, for
   example:

   .. parsed-literal::

    paster db dump --config=\ |development.ini| my_ckan_database.pg_dump

   This will create a file called ``my_ckan_database.pg_dump``, if something
   goes wrong with the CKAN upgrade you can use this file to restore the
   database to its pre-upgrade state. See :ref:`paster db` for
   details of the ``db dump`` and ``db load`` commands.

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
   |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml. This symlink
   should be updated to point to the latest schema file in
   |virtualenv|/src/ckan/ckan/config/solr/, if it doesn't already.

   For example, to update the symlink:

   .. parsed-literal::

     sudo rm /etc/solr/conf/schema.xml
     sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml /etc/solr/conf/schema.xml

6. If you are upgrading to a new major version of CKAN (for example if you
   are upgrading to CKAN 2.0, 2.1 etc.), update your CKAN database's schema
   using the ``db upgrade`` command.

   .. warning ::

     To avoid problems during the database upgrade, comment out any plugins
     that you have enabled in your ini file. You can uncomment them again when
     the upgrade finishes.

   For example:

   .. parsed-literal::

    paster db upgrade --config=\ |development.ini|

   See :ref:`paster db` for details of the ``db upgrade``
   command.

7. Rebuild your search index by running the ``ckan search-index rebuild``
   command:

   .. parsed-literal::

    paster search-index rebuild -r --config=\ |development.ini|

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

8. Finally, restart your web server. For example if you have deployed CKAN
   using the Apache web server on Ubuntu linux, run this command:

   .. parsed-literal::

    |reload_apache|

9. You're done! You should now be able to visit your CKAN website in your web
   browser and see that it's running the new version of CKAN.
