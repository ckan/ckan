========================
Post-Installation Setup
========================

After you have completed installation (from either package or source), follow this section for instructions on setting up an initial user, loading test data, and notes on deploying CKAN. 

.. note::

    If you installed CKAN from source, you will need to activate the virtualenv and switch to the ckan source directory.
    In this case, you don't need to specifiy the `--plugin` or `--config` parameters when executing the paster commands, e.g.::

        (pyenv):~/pyenv/src/ckan$ paster user list


.. _create-admin-user:

Create an Admin User
====================

By default, CKAN has a set of locked-down permissions. To begin
working with it you need to set up a user and some permissions. 

First create an admin account from the command line (you must be root, ``sudo -s``):

::

    paster --plugin=ckan user add admin --config=/etc/ckan/std/std.ini

When prompted, enter a password - this is the password you will use to log in to CKAN. In the resulting output, note that you will also get assigned a CKAN API key.

.. note :: This command is your first introduction to some important CKAN concepts. **paster** is the script used to run CKAN commands. **std.ini** is the CKAN config file. You can change options in this file to configure CKAN. 

For exploratory purposes, you might was well make the ``admin`` user a
sysadmin. You obviously wouldn't give most users these rights as they would
then be able to do anything. You can make the ``admin`` user a sysadmin like
this:

::

    paster --plugin=ckan sysadmin add admin --config=/etc/ckan/std/std.ini

You can now login to the CKAN frontend with the username ``admin`` and the password you set up.

.. _create-test-data:

Load Test Data
==============

It can be handy to have some test data to start with. You can get test data like this:

::

    paster --plugin=ckan create-test-data --config=/etc/ckan/std/std.ini

You now have a CKAN instance that you can log in to, with some test data to check everything
works.

You can also create various specialised test data collections for testing specific features of CKAN. For example, ``paster --plugin=ckan create-test-data translations`` creates some test data with some translations for testing the ckanext-multilingual extension. For more information, see:

::

    paster --plugin=ckan create-test-data --help

.. _deployment-notes:

Deployment 
==========

You may want to deploy your CKAN instance at this point, to share with others. 

If you have installed CKAN from packages, then Apache and WSGI deployment scripts are already configured for you in standard locations. 

If you have installed CKAN from source, then the standard production deployment of CKAN is Apache and WSGI, which you will need to configure yourself. For more information, see :doc:`deployment`.

