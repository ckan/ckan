============
Installation
============

After you have set up your Ubuntu 10.04 system, you can begin installing CKAN. 

.. note:: CKAN currently requires Ubuntu 10.04. Before starting, you should set up Ubuntu 10.04 using VirtualBox or Amazon EC2. See :doc:`preparation`. 

Run the Package Installer
=========================

On your Ubuntu 10.04 system, open a terminal window and switch to the root user: 

::

    sudo -s

Install the CKAN packages as follows:

::

	echo 'deb http://apt.okfn.org/ubuntu_ckan-std_dev lucid universe' > /etc/apt/sources.list.d/okfn.list
	wget -qO-  http://apt.okfn.org/packages.okfn.key | sudo apt-key add -
	apt-get update
	apt-get install ckan-std

Wait for the output to finish, then create your CKAN instance:

::

    ckan-std-install

If you are using Amazon EC2, you will additionally need to set the hostname of your server. To do this, run the command below, replacing ``ec2-46-51-149-132.eu-west-1.compute.amazonaws.com`` with the public DNS of your EC2 instance. Leave the ``/`` at the end, as it is part of the ``sed`` command. Then restart Apache. You can skip this if installing on VirtualBox or a local server. 

::

    sudo sed -e "s/ServerAlias \(.*\)/ServerAlias ec2-46-51-149-132.eu-west-1.compute.amazonaws.com/" \
             -i /etc/apache2/sites-available/std.common
    sudo /etc/init.d/apache2 restart

Finally visit your CKAN instance - either at your Amazon EC2 hostname, or at http://localhost. You'll be redirected to the login screen because you won't have set up any permissions yet, so the welcome screen will look something like this. 

.. image :: images/9.png
  :width: 807px

.. _create-admin-user:

Create an Admin User
====================

By default, CKAN has a set of locked-down permissions. To begin
working with it you need to set up a user and some permissions. 

First create an admin account from the command line (you must be root, ``sudo -s``):

::

    paster --plugin=ckan user add admin --config=/etc/ckan/std/std.ini

When prompted, enter a password - this is the password you will use to log in to CKAN. In the resulting output, note that you will also get assigned a CKAN API key.

.. note :: This command is your first introduction to some important CKAN concepts. 
    * paster is the script used to run CKAN commands. 
    * std.ini is the CKAN config file. You can change options in this file to configure CKAN. 

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

Finally, it can be handy to have some test data to start with. You can get test data like this:

::

    paster --plugin=ckan create-test-data --config=/etc/ckan/std/std.ini

You now have a CKAN instance that you can log in to, with some test data to check everything
works. 

You can now proceed to :doc:`theming`.

Deployment Notes
================

Standard production deployment of CKAN is Apache with modwsgi. 

However CKAN has been successfully deployed via a variety of other methods including Apache reverse proxy + paster, nginx reverse proxy + paster, and nginx + uwsgi.