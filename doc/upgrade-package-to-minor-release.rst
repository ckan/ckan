=========================================================
Upgrading a CKAN 2 package install to a new minor release
=========================================================

.. note::

   Before upgrading CKAN you should check the compatibility of any custom
   themes or extensions you're using, check the changelog, and backup your
   database. See :ref:`upgrading`.

Each :ref:`minor release <releases>` is distributed in its own package,
so for example CKAN ``2.0.X`` and ``2.1.X`` will be installed using the
``python-ckan_2.0_amd64.deb`` and ``python-ckan_2.1_amd64.deb`` packages
respectively.

#. Download the CKAN package for the new minor release you want to upgrade
   to (replace the version number with the relevant one)::

    wget http://packaging.ckan.org/python-ckan_2.1_amd64.deb

#. Install the package with the following command::

    sudo dpkg -i python-ckan_2.1_amd64.deb

   .. note::

      If you have changed the |apache| or |nginx| configuration files, you will
      get a prompt like the following, asking whether to keep your local changes
      or replace the files. You generally would like to keep your local changes
      (option ``N``, which is the default), but you can look at the differences
      between versions by selecting option ``D``::

       Configuration file `/etc/apache2/sites-available/ckan_default'
        ==> File on system created by you or by a script.
        ==> File also in package provided by package maintainer.
          What would you like to do about it ?  Your options are:
           Y or I  : install the package maintainer's version
           N or O  : keep your currently-installed version
             D     : show the differences between the versions
             Z     : start a shell to examine the situation
        The default action is to keep your current version.
       *** ckan_default (Y/I/N/O/D/Z) [default=N] ?

      Your local CKAN configuration file in |config_dir| will not be replaced.

   .. note::

     The install process will uninstall any existing CKAN extensions or other
     libraries located in the ``src`` directory of the CKAN virtualenv. To 
     enable them again, the installation process will iterate over all folders in
     the ``src`` directory, reinstall the requirements listed in
     ``pip-requirements.txt`` and ``requirements.txt`` files and run 
     ``python setup.py develop`` for each. If you are using a custom extension
     which does not use this requirements file name or is located elsewhere,
     you will need to manually reinstall it.

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

#. If you have any CKAN extensions installed from source, you may need to
   checkout newer versions of the extensions that work with the new CKAN
   version. Refer to the documentation for each extension. We recommend
   disabling all extensions on your ini file and re-enable them one by one
   to make sure they are working fine.

#. Rebuild your search index by running the ``ckan search-index rebuild``
   command:

   .. parsed-literal::

    sudo ckan search-index rebuild -r

   See :ref:`rebuild search index` for details of the
   ``ckan search-index rebuild`` command.

#. Finally, restart Apache:

   .. parsed-literal::

    |restart_apache|
