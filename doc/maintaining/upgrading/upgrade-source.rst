.. include:: /_substitutions.rst

==========================
Upgrading a source install
==========================

.. note::

   Before upgrading CKAN you should check the compatibility of any custom
   themes or extensions you're using, check the changelog, and backup your
   database. See :ref:`upgrading`.

The process for upgrading a source install is the same, no matter what type of
CKAN release you're upgrading to:

#. Check the :doc:`/changelog` for changes regarding the required 3rd-party
   packages and their minimum versions (e.g. web, database and search servers)
   and update their installations if necessary.

#. Activate your virtualenv and switch to the ckan source directory, e.g.:

   .. parsed-literal::

    |activate|
    cd |virtualenv|/src/ckan

#. Checkout the new CKAN version from git, for example:

   .. parsed-literal::

    git fetch
    git checkout |latest_release_tag|

   If you have any CKAN extensions installed from source, you may need to
   checkout newer versions of the extensions at this point as well. Refer to
   the documentation for each extension.

   As of CKAN 2.6 branch naming has changed. See :doc:`/contributing/release-process`
   for naming conventions. Specific patches and minor versions can be checked-out
   using tags.

#. Update CKAN's dependencies:

   ::

     pip install --upgrade -r requirements.txt


#. Register any new or updated plugins:

   ::

     python setup.py develop

#. If there have been changes in the Solr schema (check the :doc:`/changelog`
   to find out) you need to restart Jetty for the changes to take effect:

   .. parsed-literal::

    sudo service jetty restart

#. If there have been changes in the database schema (check the
   :doc:`/changelog` to find out) you need to :ref:`upgrade your database
   schema <db upgrade>`.

#. If new configuration options have been introduced (check the
   :doc:`/changelog` to find out) then check whether you need to change them
   from their default values. See :doc:`/maintaining/configuration` for
   details.

#. Rebuild your search index by running the ``ckan search-index rebuild``
   command:

   .. parsed-literal::

    ckan -c /path/to/ckan.ini search-index rebuild -r --config=\ |ckan.ini|

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

#. Finally, restart your web server. For example if you have deployed CKAN
   using a package install, run this command:

   .. parsed-literal::

    |restart_uwsgi|

#. You're done!

You should now be able to visit your CKAN website in your web browser and see
that it's running the new version of CKAN.
