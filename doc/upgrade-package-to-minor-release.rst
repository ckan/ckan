=========================================================
Upgrading a CKAN 2 package install to a new minor release
=========================================================

.. note::

   Before upgrading CKAN you should check the compatibility of any custom
   themes or extensions you're using, check the changelog, and backup your
   database. See :ref:`upgrading`.

:ref:`Minor releases <releases>` are distributed in separated packages, so
for example CKAN ``2.0.X`` and ``2.1.X`` will be installed using the
``python-ckan_2.0_amd64.deb`` and ``python-ckan_2.1_amd64.deb`` packages
respectively.

#. Download the CKAN package (replace the version number with the relevant
   one)::

    wget http://packaging.ckan.org/python-ckan_2.1_amd64.deb

#. Install the package with the following command::

    sudo dpkg -i python-ckan_2.1_amd64.deb

#. If there have been changes in the database schema (check the
   :doc:`changelog` to find out) you need to update your CKAN database's
   schema using the ``db upgrade`` command.

   .. warning ::

     To avoid problems during the database upgrade, comment out any plugins
     that you have enabled in your ini file. You can uncomment them again when
     the upgrade finishes.

   For example:

   .. parsed-literal::

    paster db upgrade --config=\ |development.ini|

   See :ref:`paster db` for details of the ``db upgrade``
   command.

#. If there have been changes in the Solr schema (check the :doc:`changelog`
   to find out) you need to update your Solr schema symlink.

   When :ref:`setting up solr` you created a symlink
   ``/etc/solr/conf/schema.xml`` linking to a CKAN Solr schema file such as
   |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml. This symlink
   should be updated to point to the latest schema file in
   |virtualenv|/src/ckan/ckan/config/solr/, if it doesn't already.

   For example, to update the symlink:

   .. parsed-literal::

     sudo rm /etc/solr/conf/schema.xml
     sudo ln -s |virtualenv|/src/ckan/ckan/config/solr/schema-2.0.xml /etc/solr/conf/schema.xml

   You will need to restart Jetty for the changes to take effect:

   .. parsed-literal::

    sudo service jetty restart

#. Rebuild your search index by running the ``ckan search-index rebuild``
   command:

   .. parsed-literal::

    sudo ckan search-index rebuild -r

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

#. Finally, restart Apache:

   .. parsed-literal::

    |restart_apache|
