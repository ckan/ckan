==============================================
Upgrading a CKAN 1 package install to CKAN 2.0
==============================================

.. note::

   If you want to upgrade a CKAN 1.x package install to a newer version of
   CKAN 1 (as opposed to upgrading to CKAN 2), see the
   `documentation <http://docs.ckan.org/en/ckan-1.8/install-from-package.html#upgrading-a-package-install>`_
   relevant to the old CKAN packaging system.

The CKAN 2.0 package requires Ubuntu 12.04 64-bit, whereas previous CKAN
packages used Ubuntu 10.04. CKAN 2.0 also introduces many
backwards-incompatible feature changes (see :doc:`the changelog <changelog>`).
So it's not possible to automatically upgrade to a CKAN 2.0 package install.

However, you can install CKAN 2.0 (either on the same server that contained
your CKAN 1.x site, or on a different machine) and then manually migrate your
database and any custom configuration, extensions or templates to your new CKAN
2.0 site. We will outline the main steps for migrating below.

#. Create a dump of your CKAN 1.x database::

    sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db dump db-1.x.dump --config=/etc/ckan/std/std.ini

#. If you want to install CKAN 2.0 on the same server that your CKAN 1.x site
   was on, uninstall the CKAN 1.x package first::

    sudo apt-get autoremove ckan

#. Install CKAN 2.0, either from a :doc:`package install <install-from-package>`
   if you have Ubuntu 12.04 64-bit, or from a
   :doc:`source install <install-from-source>` otherwise.

#. Load your database dump from CKAN 1.x into CKAN 2.0. This will migrate all
   of your datasets, resources, groups, tags, user accounts, and other data to
   CKAN 2.0. Your database schema will be automatically upgraded, and your
   search index rebuilt.

   First, activate your CKAN virtual environment and change to the ckan dir:

   .. parsed-literal::

    |activate|
    cd |virtualenv|/src/ckan

   Now, load your database. **This will delete any data already present in your
   new CKAN 2.0 database**. If you've installed CKAN 2.0 on a different
   machine from 1.x, first copy the database dump file to that machine.
   Then run these commands:

   .. parsed-literal::

     paster db clean -c |production.ini|
     paster db load -c |production.ini| db-1.x.dump

#. If you had any custom config settings in your CKAN 1.x instance that you
   want to copy across to your CKAN 2.0 instance, then update your CKAN 2.0
   |production.ini| file with these config settings. Note that not all CKAN 1.x
   config settings are still supported in CKAN 2.0, see :doc:`configuration`
   for details.

   In particular, CKAN 2.0 introduces an entirely new authorization system
   and any custom authorization settings you had in CKAN 1.x will have to be
   reconsidered for CKAN 2.0. See :doc:`authorization` for details.

#. If you had any extensions installed in your CKAN 1.x instance that you also
   want to use with your CKAN 2.0 instance, install those extensions in CKAN
   2.0. Not all CKAN 1.x extensions are compatible with CKAN 2.0. Check each
   extension's documentation for CKAN 2.0 compatibility and install
   instructions.

#. If you had any custom templates in your CKAN 1.x instance, these will need
   to be adapted before they can be used with CKAN 2.0. CKAN 2.0 introduces
   an entirely new template system based on Jinja2 rather than on Genshi.
   See :doc:`theming` for details.


