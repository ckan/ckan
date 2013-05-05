========================
Post-Installation Setup
========================

After you have completed installation (from either package or source), follow this section for instructions on setting up an initial user, loading test data, and notes on deploying CKAN. 

.. note::

   If you installed CKAN from source, you need to activate your virtualenv and
   change to your CKAN directory in order for the commands on this page to
   work. For example:

   .. parsed-literal::

     |activate|
     cd |virtualenv|/src/ckan

.. _create-admin-user:

Create a Sysadmin User
======================

You have to create your first CKAN sysadmin user from the command-line. For
example, to create a user called ``seanh`` and make him a sysadmin:

.. parsed-literal::

   paster sysadmin add seanh -c |development.ini|

If a user called ``seanh`` already exists he will be promoted to a sysadmin. If
the user account doesn't exist yet, it will be created.  You can now login to
the CKAN web interface with your sysadmin account and promote more users to
sysadmins using the web interface.

.. _create-test-data:

Load Test Data
==============

It can be handy to have some test data to start with. You can get test data like this:

.. parsed-literal::

    paster create-test-data -c |development.ini|

You now have a CKAN instance that you can log in to, with some test data to check everything
works.

You can also create various specialised test data collections for testing specific features of CKAN. For example, ``paster create-test-data translations`` creates some test data with some translations for testing the ckanext-multilingual extension. For more information, see:

::

    paster create-test-data --help

.. _deployment-notes:

Deployment
==========

You may want to deploy your CKAN instance at this point, to share with others.

If you have installed CKAN from packages, then Apache and WSGI deployment scripts are already configured for you in standard locations. 

If you have installed CKAN from source, then the standard production deployment of CKAN is Apache and WSGI, which you will need to configure yourself. For more information, see :doc:`deployment`.

