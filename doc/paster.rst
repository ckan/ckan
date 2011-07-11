Command Line Administration
+++++++++++++++++++++++++++

Paster commands provide a number of useful ways to administer a CKAN installation. These are run on the command line on the server running CKAN.

## To add: db update and db save. ##

Commands
========

  ================= ==========================================================
  changes           Distribute changes
  create-test-data  Create test data in the database.
  db                Perform various tasks on the database.
  notify            Send out modification notifications.
  ratings           Manage the ratings stored in the db
  rights            Commands relating to per-object and system-wide access rights.
  roles             Commands relating to roles and actions.
  search-index      Creates a search index for all packages
  sysadmin          Gives sysadmin rights to a named user
  user              Manage users
  ================= ==========================================================


Running paster commands
=======================

Basically the format is:: 

  paster --plugin=ckan <ckan commands> --config=<config file>

e.g.::

  paster --plugin=ckan db init --config=myckan.ini


To get a list of paster commands (i.e. including CKAN commands)::

  paster --plugin=ckan --help

And you can get help for each command. e.g.::

  paster --plugin=ckan --help db


``--plugin`` parameter
--------------------

Paster is a system-wide command, so you need to tell it to find the commands defined in the ckan code. So first parameter to paster is normally ``--plugin=ckan``.

NB: If your current directory is where CKAN's setup.py is, you don't need to specify this parameter. 

If you want to run a "paster shell" then the plugin is pylons. e.g. ``paster --plugin=pylons shell``. Often you will want to run this as the same user as the web application, to ensure log files are written as the same user. And you'll also want to specify a config file. e.g.::

  sudo -u www-data paster --plugin=pylons shell myckan.ini


``--config`` parameter
----------------------

Each server can have multiple CKAN instances running, so use this parameter to specify the CKAN config file for the instance you want to operate on. e.g. ``--config=myckan.ini``

NB: Developers tend to use development.ini, and this is the default value (looking in the current directory), so in this situation you don't need to specify this parameter.


Position of paster parameters
-----------------------------

``--plugin`` is a paster parameter, so needs to come before the CKAN command, but <code>--config</code> is a ckan parameter so needs to come after the CKAN command.

Here are three ways to express the same thing::

  paster db init
  paster --plugin=ckan db --config=development.ini init
  paster --plugin=ckan db init --config=development.ini

