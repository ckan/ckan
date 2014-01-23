.. include:: _latest_release.rst

============================
Installing CKAN from package
============================

This section describes how to install CKAN from package. This is the quickest
and easiest way to install CKAN, but it requires **Ubuntu 12.04 64-bit**. If
you're not using Ubuntu 12.04 64-bit, or if you're installing CKAN for
development, you should follow :doc:`install-from-source` instead.

At the end of the installation process you will end up with two running web
applications, CKAN itself and the DataPusher, a separate service for automatically
importing data to CKAN's :doc:`datastore`.


.. _run-package-installer:

---------------------------
1. Install the CKAN package
---------------------------

On your Ubuntu 12.04 system, open a terminal and run these commands to install
CKAN:

#. Update Ubuntu's package index::

    sudo apt-get update

#. Install the Ubuntu packages that CKAN requires::

    sudo apt-get install -y nginx apache2 libapache2-mod-wsgi libpq5

#. Download the CKAN package:

   .. parsed-literal::

      wget \http://packaging.ckan.org/|latest_package_name|

   .. note:: If ``wget`` is not present, you can install it
       via::

        sudo apt-get install wget

#. Install the CKAN package:

   .. parsed-literal::

      sudo dpkg -i |latest_package_name|

.. note:: If you get the following error it means that for some reason the
 Apache WSGI module was not enabled::

    Syntax error on line 1 of /etc/apache2/sites-enabled/ckan_default:
    Invalid command 'WSGISocketPrefix', perhaps misspelled or defined by a module not included in the server configuration
    Action 'configtest' failed.
    The Apache error log may have more information.
       ...fail!

 You can enable it by running these commands in a terminal::

    sudo a2enmod wsgi
    sudo service apache2 restart


------------------------------
2. Install PostgreSQL and Solr
------------------------------

.. tip::

   You can install |postgres|, |solr| and CKAN on different servers. Just
   change the :ref:`sqlalchemy.url` and :ref:`solr_url` settings in your
   |production.ini| file to reference your |postgres| and |solr| servers.

#. Install |postgres| and |solr|, run this command in a terminal::

    sudo apt-get install -y postgresql solr-jetty

   The install will whirr away, then towards the end you'll see this::

     * Not starting jetty - edit /etc/default/jetty and change NO_START to be 0 (or comment it out).

#. Follow the instructions in :ref:`setting up solr` to setup |solr|.

#. Follow the instructions in :ref:`postgres-setup` to setup |postgres|,
   then edit the :ref:`sqlalchemy.url` option in your |production.ini| file and
   set the correct password, database and database user.

#. Initialize your CKAN database by running this command in a terminal::

    sudo ckan db init

#. Optionally, setup the DataStore and DataPusher by following the
   instructions in :doc:`/datastore`.

#. Also optionally, you can enable file uploads by following the
   instructions in :doc:`filestore`.

---------------------------
3. Restart Apache and Nginx
---------------------------

Restart Apache and Nginx by running this command in a terminal::

    sudo service apache2 restart
    sudo service nginx restart

---------------
4. You're done!
---------------

Open http://localhost in your web browser. You should see the CKAN front
page, which will look something like this:

.. image :: /images/9.png
   :width: 807px

|

You can now move on to :doc:`/getting-started` to begin using and customizing
your CKAN site.
