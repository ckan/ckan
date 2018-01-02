===============
Getting started
===============

Once you've finished :doc:`installing CKAN <installing/index>`, this section
will walk you through getting started with your new CKAN website, including
creating a CKAN sysadmin user, some test data, and the basics of configuring
your CKAN site.


.. _create-admin-user:

------------------------
Creating a sysadmin user
------------------------

You have to use CKAN's command line interface to create your first sysadmin
user, and it can also be useful to create some test data from the command line.
For full documentation of CKAN's command line interface (including
troubleshooting) see :doc:`paster`.

.. note::

   CKAN commands are executed using the ``paster`` command on the server that
   CKAN is installed on.  Before running the paster commands below, you need to
   make sure that your virtualenv is activated and that you're in your ckan
   source directory.  For example:

   .. parsed-literal::

      |activate|
      cd |virtualenv|/src/ckan

You have to create your first CKAN sysadmin user from the command line. For
example, to create a new user called ``seanh`` and make him a sysadmin:

.. parsed-literal::

   paster sysadmin add seanh email=seanh@localhost name=seanh -c |production.ini|
   
You'll be prompted to enter a password during account creation.

Or, if you already have an existing user, you could promote him to a sysadmin:

.. parsed-literal::

   paster sysadmin add seanh -c |production.ini|

For a list of other command line commands for managing sysadmins, run::

 paster sysadmin --help

Read the :doc:`/sysadmin-guide` to learn what you can do as a
CKAN sysadmin.

.. _create-test-data:

------------------
Creating test data
------------------

It can be handy to have some test data to start with, to quickly check that
everything works. You can add a standard set of test data to your site from the
command line with the ``create-test-data`` command:

.. parsed-literal::

   paster create-test-data -c |production.ini|

If you later want to delete this test data and start again with an empty
database, you can use the :ref:`db clean <db clean>` command.

For a list of other command line commands for creating tests data, run::

 paster create-test-data --help

-----------
Config file
-----------

All of the options that can be set in the admin page and many more can be set
by editing CKAN's config file. By default, the config file is located at
|development.ini| for development sites or |production.ini| for production
sites. The config file can be edited in any text editor. For example, to change
the title of your site you would find the ``ckan.site_title`` line in your
config file and edit it::

    ckan.site_title = Masaq Data Hub

Make sure the line is not commented-out (lines in the config file that begin
with ``#`` are considered comments, so if there's a ``#`` at the start of a
line you've edited, delete it), save the file, and then restart your web server
for the changes to take effect. For example, if using Apache on Ubuntu:

.. parsed-literal::

   |reload_apache|

For full documentation of CKAN's config file and all the options you can set,
see :doc:`configuration`.

.. note::

   If the same option is set in both the config file and in the admin page,
   the admin page setting takes precedence. You can use the *Reset* button on
   the admin page to clear your settings, and allow settings from the config
   file to take effect.
