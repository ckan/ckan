.. include:: /_substitutions.rst

============================
Installing CKAN from package
============================

This section describes how to install CKAN from package. This is the quickest
and easiest way to install CKAN, but it requires **Ubuntu 18.04 (Python 2) or 20.04 (Python 3 or Python 2) 64-bit**. If
you're not using any of these Ubuntu versions, or if you're installing CKAN for
development, you should follow :doc:`install-from-source` instead.

At the end of the installation process you will end up with two running web
applications, CKAN itself and the DataPusher, a separate service for automatically
importing data to CKAN's :doc:`/maintaining/datastore`. Additionally, there will be a process running the worker for running :doc:`/maintaining/background-tasks`. All these processes will be managed by `Supervisor <https://supervisord.org/>`_.

For Python 3 installations, the minimum Python version required is 3.6.

* **Ubuntu 20.04** includes **Python 3.8** as part of its distribution
* **Ubuntu 18.04** includes **Python 3.6** as part of its distribution


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
    | Solr/Jetty | 8983       | Search    |
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

   .. note:: If you want to install CKAN 2.9 running on Python 2 for backwards compatibility, you need to also install the Python 2 libraries:

    .. parsed-literal::

       # On Ubuntu 18.04
       sudo apt install python2 libpython2.7

       # On Ubuntu 20.04
       sudo apt install libpython2.7

#. Download the CKAN package:

    - On Ubuntu 18.04:

       .. parsed-literal::

           wget \http://packaging.ckan.org/|latest_package_name_bionic|

     - On Ubuntu 20.04, for Python 3 (recommended):

       .. parsed-literal::

           wget \http://packaging.ckan.org/|latest_package_name_focal_py3|

     - On Ubuntu 20.04, for Python 2:

       .. parsed-literal::

           wget \http://packaging.ckan.org/|latest_package_name_focal_py2|

#. Install the CKAN package:

   - On Ubuntu 18.04:

       .. parsed-literal::

           sudo dpkg -i |latest_package_name_bionic|

   - On Ubuntu 20.04, for Python 3:

       .. parsed-literal::

           sudo dpkg -i |latest_package_name_focal_py3|

   - On Ubuntu 20.04, for Python 2:

       .. parsed-literal::

           sudo dpkg -i |latest_package_name_focal_py2|


-----------------------------------
2. Install and configure PostgreSQL
-----------------------------------

.. tip::

   You can install |postgres| and CKAN on different servers. Just
   change the :ref:`sqlalchemy.url` setting in your
   |ckan.ini| file to reference your |postgres| server.

.. note::

   The commands mentioned below are tested for Ubuntu system

Install |postgres|, running this command in a terminal::

    sudo apt install -y postgresql

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

Install |solr|, running this command in a terminal::

    sudo apt install -y solr-tomcat

.. include:: solr.rst

-------------------------------------------------------
4. Update the configuration and initialize the database
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
5. Start the Web Server and restart Nginx
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
6. You're done!
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

