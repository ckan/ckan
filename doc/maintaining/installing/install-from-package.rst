.. include:: /_substitutions.rst

============================
Installing CKAN from package
============================

This section describes how to install CKAN from package. This is the quickest
and easiest way to install CKAN, but it requires **Ubuntu 20.04 or 22.04 64-bit**. If
you're not using any of these Ubuntu versions, or if you're installing CKAN for
development, you should follow :doc:`install-from-source` instead.

At the end of the installation process you will end up with two running web
applications, CKAN itself and the DataPusher, a separate service for automatically
importing data to CKAN's :doc:`/maintaining/datastore`. Additionally, there will be a process running the worker for running :doc:`/maintaining/background-tasks`. All these processes will be managed by `Supervisor <https://supervisord.org/>`_.

For Python 3 installations, the minimum Python version required is 3.7.

Host ports requirements:

    +------------+------------+-----------+
    | Service    | Port       | Used for  |
    +============+============+===========+
    | NGINX      | 80         | Proxy     |
    +------------+------------+-----------+
    | uWSGI      | 8080       | Web Server|
    +------------+------------+-----------+
    | uWSGI      | 8800       | DataPusher|
    +------------+------------+-----------+
    | Solr       | 8983       | Search    |
    +------------+------------+-----------+
    | PostgreSQL | 5432       | Database  |
    +------------+------------+-----------+
    | Redis      | 6379       | Search    |
    +------------+------------+-----------+


.. _run-package-installer:

---------------------------
1. Install the CKAN package
---------------------------

On your Ubuntu system, open a terminal and run these commands to install
CKAN:


#. Update Ubuntu's package index::

    sudo apt update

#. Install the Ubuntu packages that CKAN requires (and 'git', to enable you to install CKAN extensions)::

    sudo apt install -y libpq5 redis-server nginx supervisor

#. Download the CKAN package:

  - On Ubuntu 20.04:

       .. parsed-literal::

            wget \https://packaging.ckan.org/|current_package_name_focal|

  - On Ubuntu 22.04:

       .. parsed-literal::

            wget \https://packaging.ckan.org/|current_package_name_jammy|

#. Install the CKAN package:

  - On Ubuntu 20.04:

       .. parsed-literal::

            sudo dpkg -i |current_package_name_focal|

  - On Ubuntu 22.04:

       .. parsed-literal::

            sudo dpkg -i |current_package_name_jammy|


-----------------------------------
2. Install and configure PostgreSQL
-----------------------------------

.. tip::

   You can install |postgres| and CKAN on different servers. Just
   change the :ref:`sqlalchemy.url` setting in your
   |ckan.ini| file to reference your |postgres| server.

.. note::

   The commands mentioned below are tested in Ubuntu

.. include:: postgres.rst

Edit the :ref:`sqlalchemy.url` option in your :ref:`config_file` (|ckan.ini|) file and
set the correct password, database and database user.


-----------------------------
3. Install and configure Solr
-----------------------------

.. tip::

   You can install |solr| and CKAN on different servers. Just
   change the :ref:`solr_url` setting in your
   |ckan.ini| |production.ini| file to reference your |solr| server.

.. include:: solr.rst


------------------------------
4. Set up a writable directory
------------------------------

CKAN needs a directory where it can write certain files, regardless of whether you
are using the :doc:`/maintaining/filestore` or not (if you do want to enable file uploads,
set the :ref:`ckan.storage_path` configuration option in the next section).

1. Create the directory where CKAN will be able to write files:

   .. parsed-literal::

     sudo mkdir -p |storage_path|

2. Set the permissions of this directory.
   For example if you're running CKAN with Nginx, then the Nginx's user
   (``www-data`` on Ubuntu) must have read, write and execute permissions on it:

   .. parsed-literal::

     sudo chown www-data |storage_path|
     sudo chmod u+rwx |storage_path|



-------------------------------------------------------
5. Update the configuration and initialize the database
-------------------------------------------------------

#. Edit the :ref:`config_file` (|ckan.ini|) to set up the following options:

    site_id
      Each CKAN site should have a unique ``site_id``, for example::

        ckan.site_id = default

    site_url
      Provide the site's URL. For example::

        ckan.site_url = http://demo.ckan.org

#. Initialize your CKAN database by running this command in a terminal::

    sudo ckan db init

#. Optionally, setup the DataStore and DataPusher by following the
   instructions in :doc:`/maintaining/datastore`.

#. Also optionally, you can enable file uploads by following the
   instructions in :doc:`/maintaining/filestore`.

-----------------------------------------
6. Start the Web Server and restart Nginx
-----------------------------------------

Reload the Supervisor daemon so the new processes are picked up::

    sudo supervisorctl reload

After a few seconds run the following command to check the status of the processes::

    sudo supervisorctl status

You should see three processes running without errors::

    ckan-datapusher:ckan-datapusher-00   RUNNING   pid 1963, uptime 0:00:12
    ckan-uwsgi:ckan-uwsgi-00             RUNNING   pid 1964, uptime 0:00:12
    ckan-worker:ckan-worker-00           RUNNING   pid 1965, uptime 0:00:12

If some of the processes reports an error, make sure you've run all the previous steps and check the logs located in ``/var/log/ckan`` for more details.

Restart Nginx by running this command::

    sudo service nginx restart

---------------
7. You're done!
---------------

Open http://localhost in your web browser. You should see the CKAN front
page, which will look something like this:

.. image :: /images/9.png
   :width: 807px

|

You can now move on to :doc:`/maintaining/getting-started` to begin using and customizing
your CKAN site.

.. note:: The default authorization settings on a new install are deliberately
    restrictive. Regular users won't be able to create datasets or organizations.
    You should check the :doc:`/maintaining/authorization` documentation, configure CKAN accordingly
    and grant other users the relevant permissions using the :ref:`sysadmin account <create-admin-user>`.

.. note::

   There may be a ``PermissionError: [Errno 13] Permission denied:`` message when restarting supervisor or 
   accessing CKAN via a browser for the first time. This happens when a different user is used to execute 
   the web server process than the user who installed CKAN and the support software. A workaround would be to 
   open up the permissions on the ``/usr/lib/ckan/default/src/ckan/ckan/public/base/i18n/`` directory 
   so that this user could write the .js files into it. Accessing CKAN will generate these files for a new 
   install, or you could run ``ckan -c /etc/ckan/default/ckan.ini translation js`` to explicitly generate them.
