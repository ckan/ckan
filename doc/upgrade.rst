============
Upgrade CKAN
============

Any time you want to upgrade CKAN to a newer version, first back up your database:

::

   paster --plugin=ckan db dump demo_ckan_backup.pg_dump --config=demo.ckan.net.ini

Then run this as root:

::

    apt-get update
    apt-get dist-upgrade
    ckan-std-install

You need to use ``dist-upgrade`` rather than ``upgrade`` because it is possible
more recent versions of CKAN will add new dependencies rather than just
updating existing ones, and apt will only install new dependencies if you use
``dist-upgrade``. 

The ``ckan-std-install`` will also upgrade your existing CKAN
instance, keeping a backup of your old CKAN config file.
