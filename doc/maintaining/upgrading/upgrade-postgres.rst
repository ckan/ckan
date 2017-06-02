===========================================
Upgrading Postgres for the CKAN 2.6 release
===========================================


CKAN 2.6 requires |postgres| to be of version 9.2 or later (previously it was
8.4). This is a guide to doing the upgrade if necessary.

What are CKAN's |postgres| connection settings?
===============================================

Find out the |postgres| connection settings, as used by CKAN and Datastore:

.. parsed-literal::

   grep sqlalchemy.url |production.ini|
   grep ckan.datastore.write_url |production.ini|

where the format of the connection strings is one of these::

   postgres://USERNAME:PASSWORD@HOST/DBNAME
   postgres://USERNAME:PASSWORD@HOST:PORT/DBNAME

.. note::

   If the 'host' is not configured as ``localhost`` then CKAN is using a
   |postgres| that is running on another machine. In this case, many of the
   commands below will need running on the remote machine, or if you also have
   |postgres| installed on the CKAN machine then |postgres| tools can usually
   run them on the remote host by using the --host parameter.

What version are you running?
=============================

To ask |postgres| its version::

    sudo -u postgres psql -c 'SHOW server_version;'

Or if |postgres| is on a remote host then you can either run the command on
that machine or if you have psql installed locally you can use::

    psql --host=HOSTNAME --username=USERNAME -W -c 'SHOW server_version;'

(replace `HOSTNAME` and `USERNAME` with the values from your connection
settings, as previously mentioned. It will prompt you for the password).

The version will look like this::

    server_version
    ----------------
    9.1.9 
    (1 row)

Ignoring the last number of the three, if your |postgres| version number is
lower than 9.2 then you should upgrade |postgres| before you upgrade to CKAN
2.5 or later.

Upgrading
=========

.. note::

   These instructions install the new |postgres| version alongside the existing
   one, so any install issues can be dealt before switching. However it is
   still wise to test the whole process on a test machine before upgrading for
   a public-facing CKAN.

.. note::

   These instructions are for Ubuntu, but can be adapted to other distributions.

#. If the |postgres| cluster that ckan uses is not running on localhost then
   log-in to the |postgres| machine now.

#. Check to see what |postgres| packages are installed::

     aptitude search '~i postgres'

   These instructions assume you have been using the installed package
   ``postgresql-9.1``. If using ckanext-spatial then you will also have PostGIS
   too (e.g. ``postgresql-9.1-postgis``), which needs upgrading at the same time.

#. Install the Postgres Apt repository, containing newer versions. This is for
   Ubuntu 12.04 (Precise) - for other versions and more information, refer to:
   http://www.postgresql.org/download/linux/ubuntu/ ::

     echo 'deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main' | sudo tee /etc/apt/sources.list.d/pgdg.list
     wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
     sudo apt-get update
     aptitude search postgresql-9.

   You should now see there are packages for postgresql-9.4 etc.

#. Install the newer |postgres| version. It is suggested you pick the newest stable version (from those listed in the previous step). At the time of writing, 9.5 is listed but is actually still an alpha version, so instead we'll use 9.4::

     sudo apt-get install postgresql-9.4

   And if you need PostGIS::

     sudo apt-get install postgresql-9.4-postgis

#. If you have customized any |postgres| options, insert them into the new version's config files.

   You can probably just copy the authentication rules straight::

     sudo cp /etc/postgresql/9.1/main/pg_hba.conf /etc/postgresql/9.4/main/pg_hba.conf

   And you should read through the differences in postgresql.conf. This is a handy way to do this whilst ignoring changes in the comment lines::

     diff -u -B <(grep -vE '^\s*(#|$)' /etc/postgresql/9.1/main/postgresql.conf)  <(grep -vE '^\s*(#|$)' /etc/postgresql/9.4/main/postgresql.conf)

   Once you've finished your changes, restart both versions of |postgres|::

     sudo /etc/init.d/postgresql restart 9.4

#. Follow the instructions in :ref:`postgres-setup` to setup |postgres| with a user and database. Ensure your username, password and database name match those in your connection settings (see previous section.)

#. Now log-in to the CKAN machine, if you have a separate |postgres| machine.

#. Activate your virtualenv and switch to the ckan source directory, e.g.:

   .. parsed-literal::

    |activate|
    cd |virtualenv|/src/ckan

#. Stop your server to prevent further writes to the database (because those
   changes would be lost)::

     sudo service apache2 stop

#. Create a back-up of the database roles::

     sudo -u postgres pg_dumpall --roles-only > backup_roles.sql

   or for a remote database::

     pg_dumpall --host=HOSTNAME --username=USERNAME -W --roles-only -f backup_roles.sql

#. Make a note of the names of all the databases in your |postgres| so that you
   can create dumps of them. List them using::

     sudo -u postgres psql -l

   or remotely::

     psql --host=HOSTNAME --username=USERNAME -W -l 

   The databases listed should comprise:

     * CKAN database - as given in `sqlalchemy.url`. Default: '|database|'
     * Datastore database - as given in `ckan.datastore.write_url`. Default: '|datastore|'
     * `template0` - should not be dumped
     * `template1` - you'll only need to dump this if you have edited it for some reason

   You may also have:

     * Test CKAN database - default '|test_database|'
     * Test Datastore database - default '|test_datastore|'

   which do not need to be migrated - they will be regenerated later on.

   .. warning::

     If you have other databases apart from these (or have created any
     |postgres| tablespaces) then you'll have to decide how to deal with them -
     they are outside the scope of this guide.

#. Create the backups of the databases you are migrating e.g.:

   .. parsed-literal::

     sudo -u postgres pg_dump -Fc -b -v |database| > backup_ckan.sql
     sudo -u postgres pg_dump -Fc -b -v |datastore| > backup_datastore.sql

   or remotely:

   .. parsed-literal::

     pg_dump --host=HOSTNAME --username=USERNAME -W |database| -f backup_ckan.sql
     pg_dump --host=HOSTNAME --username=USERNAME -W |datastore| -f backup_datastore.sql

   You need to use the `-Fc -b` options because that is required by PostGIS migration.

#. Optional: If necessary, update the PostGIS objects (known as a 'hard upgrade'). Please refer to the `documentation <http://postgis.net/docs/postgis_installation.html#hard_upgrade>`_ if you find any issues. ::

     perl /usr/share/postgresql/9.4/contrib/postgis-2.1/postgis_restore.pl backup_ckan.sql > backup_ckan_postgis.sql

#. Restore your |postgres| roles into the new |postgres| version cluster. If
   you're not upgrading to |postgres| version 9.4, you'll need to change the
   number in this psql command and future ones too. So::

     sudo -u postgres psql --cluster 9.4/main -f backup_roles.sql

   Expect there will be one error::

     psql:backup_roles.sql:22: ERROR:  role "postgres" already exists

   which you can ignore - it should carry on regardless and finish ok.

#. Create the databases:

   .. parsed-literal::

        sudo -u postgres createdb --cluster 9.4/main |database|
        sudo -u postgres createdb --cluster 9.4/main |datastore|

#. Optional: If necessary, enable PostGIS on the main database:

   .. parsed-literal::

        sudo -u postgres psql --cluster 9.4/main -d |database| -f /usr/share/postgresql/9.4/contrib/postgis-2.1/postgis.sql
        sudo -u postgres psql --cluster 9.4/main -d |database| -f /usr/share/postgresql/9.4/contrib/postgis-2.1/spatial_ref_sys.sql
        sudo -u postgres psql --cluster 9.4/main -d |database| -c 'ALTER TABLE geometry_columns OWNER TO ckan_default;'
        sudo -u postgres psql --cluster 9.4/main -d |database| -c 'ALTER TABLE spatial_ref_sys OWNER TO ckan_default;'

   To check if PostGIS was properly installed:

   .. parsed-literal::

        sudo -u postgres psql --cluster 9.4/main -d |database| -c "SELECT postgis_full_version()"


#. Now restore your databases::

     sudo -u postgres psql --cluster 9.4/main -f backup_ckan.sql
     sudo -u postgres psql --cluster 9.4/main -f backup_datastore.sql

   .. note:

      If you get encoding errors like:``encoding "UTF8" does not match locale
      "en_US"`` it is probably because the encoding of the new cluster is
      different to the previous one. This can be seen when you use psql -l for
      template0. You can usually solve it by deleting and recreate the new cluster
      in UTF8 encoding, before retrying the restore::

        sudo pg_dropcluster --stop 9.4 main
        sudo pg_createcluster --start 9.4 main --locale=en_US.UTF-8


#. Tell CKAN to use the new |postgres| database by switching the |postgres| port number in the |production.ini|. First find the correct port::

     sudo pg_lsclusters

   It is likely that the old |postgres| is port 5432 and the new one is on 5433.

   Now edit the |production.ini| to insert the port number into the `sqlalchemy.url`. e.g.:

   .. parsed-literal::

     sqlalchemy.url = postgresql://|database_user|:pass@localhost:5433/|database|

   And restart CKAN e.g.::

     |restart_apache|

#. If you run the ckan tests then you should recreate the test databases, as described in :doc:`../../contributing/test`.

#. Once you are happy everything is running ok, you can delete your old |postgres| version's config and database files::

     sudo apt-get purge postgresql-9.1

   If you also have PostGIS installed, remove that too::

     sudo apt-get remove postgresql-9.1-postgis

#. Download the CKAN package for the new minor release you want to upgrade
   to (replace the version number with the relevant one)::

    wget http://packaging.ckan.org/python-ckan_2.5_amd64.deb

