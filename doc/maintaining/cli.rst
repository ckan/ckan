.. _cli:

============================
Command Line Interface (CLI)
============================

.. note::

    From CKAN 2.9 onwards the CKAN configuration file is named 'ckan.ini'.
    Previous names: 'production.ini' and 'development.ini' (plus others) may
    also still appear in documentation and the software. These legacy names
    will eventually be phased out.

.. note::

    From CKAN 2.9 onwards, the ``paster`` command used for common CKAN
    administration tasks has been replaced with the  ``ckan`` command.

If you have trouble running 'ckan' CLI commands, see
`Troubleshooting ckan Commands`_ below.

.. note::

   Once you activate your CKAN virtualenv the "ckan" command is available from within any
   location within the host environment.

   To run a ckan command without activating the virtualenv first, you have
   to give the full path the ckan script within the virtualenv, for example:

   .. parsed-literal::

      |virtualenv|/bin/ckan -c |ckan.ini| user list

   In the example commands below, we assume you're running the commands with
   your virtualenv activated and from your ckan directory.

The general form of a CKAN ``ckan`` command is:

.. parsed-literal::

 ckan --config=\ |ckan.ini| **command**

The `` --config`` option tells CKAN where to find your config file, which it
reads for example to know which database it should use. As you'll see in the
examples below, this option can be given as ``-c`` for short.

The config file (ckan.ini) will generally be located in the
``/etc/ckan/default/`` directory however it can be located in any directory on
the host machine

**command** should be replaced with the name of the CKAN command that you wish
to execute. Most commands have their own subcommands and options.

.. note::

  You may also specify the location of your config file using the CKAN_INI
  environment variable. You will no longer need to use --config= or -c to
  tell ckan where the config file is:


.. parsed-literal::

 export CKAN_INI=\ |ckan.ini|

.. note::

  You can run the ckan command in the same directory as the
  CKAN config file when the config file is named 'ckan.ini'. You will
  not be required to use --config or -c in this case. For backwards compatibility, the config file can be also named 'development.ini', but this usage is deprecated
  and will be phased out in a future CKAN release.

.. parsed-literal::

 cd |virtualenv|\/src/ckan; ckan command


Commands and Subcommands

.. parsed-literal::

 ckan -c |ckan.ini| user list

(Here ``user`` is the name of the CKAN command you're running, and ``list`` is
a subcommand of ``user``.)

For a list of all available commands, see `CKAN Commands Reference`_.

Each command has its own help text, which tells you what subcommands and
options it has (if any). To print out a command's help text, run the command
with the ``--help`` option, for example:

.. parsed-literal::

 ckan -c |ckan.ini| user --help


-------------------------------
Troubleshooting ckan Commands
-------------------------------

Permission Error
================

If you receive 'Permission Denied' error, try running ckan with sudo.

.. parsed-literal::

 sudo |virtualenv|/bin/ckan -c |ckan.ini| db clean

Virtualenv not activated, or not in ckan dir
============================================

Most errors with ckan commands can be solved by remembering to **activate
your virtual environment** and **change to the ckan directory** before running
the command:

.. parsed-literal::

 |activate|
 cd |virtualenv|/src/ckan

Error messages such as the following are usually caused by forgetting to do
this:

* **Command 'foo' not known** (where *foo* is the name of the command you
  tried to run)
* **The program 'ckan' is currently not installed**
* **Command not found: ckan**
* **ImportError: No module named webassets** (or other ``ImportError``\ s)

Running ckan commands provided by extensions
==============================================

**If you're trying to run a CKAN command provided by an extension** that you've
installed and you're getting an error like **Command 'foo' not known** even
though you've activated your virtualenv, make sure that you have added the relevant plugin to the :ref:`ckan.plugins` setting in the ini file.

Wrong config file path
======================

AssertionError: Config filename development.ini does not exist
  This means you forgot to give the ``--config`` or ``-c`` option to tell CKAN
  where to find your config file. (CKAN looks for a config file named
  ``development.ini`` in your current working directory by default.)

ConfigParser.MissingSectionHeaderError: File contains no section headers
  This happens if the config file that you gave with the ``-c`` or ``--config``
  option is badly formatted, or if you gave the wrong filename.

IOError: [Errno 2] No such file or directory: '...'
  This means you gave the wrong path to the ``--config`` or ``-c`` option
  (you gave a path to a file that doesn't exist).


-------------------------
ckan Commands Reference
-------------------------

The following ckan commands are supported by CKAN:

================= ============================================================
asset             WebAssets commands.
config            Search, validate, describe config options
config-tool       Tool for editing options in a CKAN config file
datapusher        Perform commands in the datapusher.
dataset           Manage datasets.
datastore         Perform commands to set up the datastore.
db                Perform various tasks on the database.
generate          Generate empty extension files to expand CKAN
jobs              Manage background jobs
sass              Compile all root sass documents into their CSS counterparts
notify            Send out modification notifications.
plugin-info       Provide info on installed plugins.
profile           Code speed profiler.
run               Start Development server.
search-index      Creates a search index for all datasets
seed              Create test data in the database.
sysadmin          Gives sysadmin rights to a named user.
tracking          Update tracking statistics.
translation       Translation helper functions
user              Manage users.
views             Create views on relevant resources
================= ============================================================


asset: WebAssets commands
==================================

Usage

.. parsed-literal::

 ckan asset build            - Builds bundles, regardless of whether they are changed or not
 ckan asset watch            - Start a daemon which monitors source files, and rebuilds bundles
 ckan asset clean            - Will clear out the cache, which after a while can grow quite large


.. _cli.ckan.config:

config: Search, validate, describe config options
=================================================

Usage

.. parsed-literal::

  ckan config declaration [PLUGIN...]  - Print declared config options for the given plugins.
  ckan config describe [PLUGIN..]      - Print out config declaration for the given plugins.
  ckan config search [PATTERN]         - Print all declared config options that match pattern.
  ckan config undeclared               - Print config options that has no declaration.
  ckan config validate                 - Validate global configuration object against declaration.



config-tool: Tool for editing options in a CKAN config file
===========================================================

Usage

.. parsed-literal::

 ckan config-tool --section (-s)  - Section of the config file
 ckan config-tool --edit (-e)     - Checks the option already exists in the config file
 ckan config-tool --file (-f)     - Supply an options file to merge in

Examples

.. parsed-literal::

 ckan config-tool |ckan.ini| sqlalchemy.url=123 'ckan.site_title=ABC'
 ckan config-tool |ckan.ini| -s server:main -e port=8080
 ckan config-tool |ckan.ini| -f custom_options.ini


datapusher: Perform commands in the datapusher
==============================================

Usage

.. parsed-literal::

 ckan datapusher resubmit    - Resubmit udated datastore resources
 ckan datapusher submit      - Submits resources from package


dataset: Manage datasets
========================

Usage

.. parsed-literal::

 ckan dataset DATASET_NAME|ID            - shows dataset properties
 ckan dataset show DATASET_NAME|ID       - shows dataset properties
 ckan dataset list                       - lists datasets
 ckan dataset delete [DATASET_NAME|ID]   - changes dataset state to 'deleted'
 ckan dataset purge [DATASET_NAME|ID]    - removes dataset from db entirely


datastore: Perform commands in the datastore
===================================================

Make sure that the datastore URLs are set properly before you run these commands.

Usage

.. parsed-literal::

 ckan datastore set-permissions  - generate SQL for permission configuration
 ckan datastore dump             - dump a datastore resource
 ckan datastore purge            - purge orphaned datastore resources


db: Manage databases
====================

.. parsed-literal::

 ckan db clean               - Clean the database
 ckan db downgrade           - Downgrade the database
 ckan db duplicate_emails    - Check users email for duplicate
 ckan db init                - Initialize the database
 ckan db pending-migrations  - List all sources with unapplied migrations.
 ckan db upgrade             - Upgrade the database
 ckan db version             - Returns current version of data schema

See :doc:`database-management`.


generate: Scaffolding for regular development tasks
===================================================

Usage

.. parsed-literal::

 ckan generate config        -  Create a ckan.ini file.
 ckan generate extension     -  Create empty extension.
 ckan generate fake-data     -  Generate random entities of the given category.
 ckan generate migration     -  Create new alembic revision for DB migration.


.. _cli jobs:

jobs: Manage background jobs
============================

.. parsed-literal::

 ckan jobs cancel      - cancel a specific job.
 ckan jobs clear       - cancel all jobs.
 ckan jobs list        - list jobs.
 ckan jobs show        - show details about a specific job.
 ckan jobs test        - enqueue a test job.
 ckan jobs worker      - start a worker

The ``jobs`` command can be used to manage :ref:`background jobs`.

.. versionadded:: 2.7

.. _cli jobs worker:

Run a background job worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs worker [--burst] [QUEUES]

Starts a worker that fetches job from the :ref:`job queues <background jobs
queues>` and executes them. If no queue names are given then it listens to
the default queue. This is equivalent to

.. parsed-literal::

 ckan -c |ckan.ini| jobs worker default

If queue names are given then the worker listens to those queues and only
those:

.. parsed-literal::

 ckan -c |ckan.ini| jobs worker my-custom-queue another-special-queue

Hence, if you want the worker to listen to the default queue and some others
then you must list the default queue explicitly

.. parsed-literal::

 ckan -c |ckan.ini| jobs worker default my-custom-queue

If the ``--burst`` option is given then the worker will exit as soon as all its
queues are empty. Otherwise it will wait indefinitely until a new job is
enqueued (this is the default).

.. note::

    In a production setting you should :ref:`use a more robust way of running
    background workers <background jobs supervisor>`.


.. _cli jobs list:

List enqueued jobs
^^^^^^^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs list [QUEUES]

Lists the currently enqueued jobs from the given :ref:`job queues <background
jobs queues>`. If no queue names are given then the jobs from all queues are
listed.


.. _cli jobs show:

Show details about a job
^^^^^^^^^^^^^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs show ID

Shows details about the enqueued job with the given ID.


.. _cli jobs cancel:

Cancel a job
^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs cancel ID

Cancels the enqueued job with the given ID. Jobs can only be canceled while
they are enqueued. Once a worker has started executing a job it cannot be
aborted anymore.


.. _cli jobs clear:

Clear job queues
^^^^^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs clear [QUEUES]

Cancels all jobs on the given :ref:`job queues <background jobs queues>`. If no
queues are given then *all* queues are cleared.


.. _cli jobs test:

Enqueue a test job
^^^^^^^^^^^^^^^^^^

.. parsed-literal::

 ckan -c |ckan.ini| jobs test [QUEUES]

Enqueues a test job. If no :ref:`job queues <background jobs queues>` are given
then the job is added to the default queue. If queue names are given then a
separate test job is added to each of the queues.


.. _sass:

sass: Compile all root sass documents into their CSS counterparts
=================================================================

Usage

.. parsed-literal::

 sass


notify: Send out modification notifications
===========================================

Usage

.. parsed-literal::

 ckan notify replay    - send out modification signals. In "replay" mode,
                       an update signal is sent for each dataset in the database.


plugin-info: Provide info on installed plugins
==============================================

As the name suggests, this commands shows you the installed plugins (based on the .ini file) , their description, and which interfaces they implement


profile: Code speed profiler
============================

Provide a ckan url and it will make the request and record how long each function call took in a file that can be read
by runsnakerun.

Usage

.. parsed-literal::

 ckan profile URL

The result is saved in profile.data.search. To view the profile in runsnakerun::

   runsnakerun ckan.data.search.profile

You may need to install the cProfile python module.


run: Start Development server
==================================

Usage

.. parsed-literal::

 ckan run --host (-h)                  - Set Host
 ckan run --port (-p)                  - Set Port
 ckan run --disable-reloader (-r)      - Use reloader
 ckan run --passthrough_errors         - Crash instead of handling fatal errors

Use ``--passthrough-errors`` to enable pdb
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Exceptions are caught and handled by CKAN. Sometimes, user needs to disable
this error handling, to be able to use ``pdb`` or the debug capabilities of the
most common IDE. This allows to use breakpoints, inspect the stack frames and
evaluate arbitrary Python code.
Running CKAN with ``--passthrough-errors`` will automatically disable CKAN
reload capabilities and run everything in a single process, for the sake of
simplicity.

Example:

 python -m pdb ckan run --passthrough-errors


search-index: Search index commands
===================================

Usage

.. parsed-literal::

 ckan search-index check                    - Check search index
 ckan search-index clear                    - Clear the search index
 ckan search-index rebuild                  - Rebuild search index
 ckan search-index rebuild-fast             - Reindex with multiprocessing
 ckan search-index show                     - Show index of a dataset


.. _rebuild search index:

search-index: Rebuild search index
==================================

Rebuilds the search index. This is useful to prevent search indexes from getting out of sync with the main database.

For example

.. parsed-literal::

 ckan -c |ckan.ini| search-index rebuild

This default behaviour will refresh the index keeping the existing indexed datasets and rebuild it with all datasets. If you want to rebuild it for only
one dataset, you can provide a dataset name

.. parsed-literal::

 ckan -c |ckan.ini| search-index rebuild test-dataset-name

Alternatively, you can use the `-o` or `--only-missing` option to only reindex datasets which are not
already indexed

.. parsed-literal::

 ckan -c |ckan.ini| search-index rebuild -o

There is also an option available which works like the refresh option but tries to use all processes on the
computer to reindex faster

.. parsed-literal::

 ckan -c |ckan.ini| search-index rebuild-fast

There is also an option to clear the whole index first and then rebuild it with all datasets:

.. parsed-literal::

 ckan -c |ckan.ini| search-index rebuild --clear

There are other search related commands, mostly useful for debugging purposes

.. parsed-literal::

 ckan search-index check                  - checks for datasets not indexed
 ckan search-index show DATASET_NAME      - shows index of a dataset
 ckan search-index clear [DATASET_NAME]   - clears the search index for the provided dataset or for the whole ckan instance


sysadmin: Give sysadmin rights
==============================

Usage

.. parsed-literal::

 ckan sysadmin add       - convert user into a sysadmin
 ckan sysadmin list      - list sysadmins
 ckan sysadmin remove    - removes user from sysadmins

For example, to make a user called 'admin' into a sysadmin

.. parsed-literal::

 ckan -c |ckan.ini| sysadmin add admin


tracking: Update tracking statistics
====================================

Usage

.. parsed-literal::

 ckan tracking update [start_date]       - update tracking stats
 ckan tracking export FILE [start_date]  - export tracking stats to a csv file


translation: Translation helper functions
=========================================

Usage

.. parsed-literal::

 ckan translation js          - generate the JavaScript translations
 ckan translation mangle      - mangle the zh_TW translations for testing
 ckan translation check-po    - check po files for common mistakes

.. note::

    Since version 2.7 the JavaScript translation files are automatically
    regenerated if necessary when CKAN is started. Hence you usually do not
    need to run ``ckan translation js`` manually.


.. _cli-user:

user: Create and manage users
=============================

Lets you create, remove, list and manage users.

Usage

.. parsed-literal::

 ckan user add         - add new user
 ckan user list        - list all users
 ckan user remove      - remove user
 ckan user setpass     - set password for the user
 ckan user show        - show user

For example, to create a new user called 'admin'

.. parsed-literal::

 ckan -c |ckan.ini| user add admin

To delete the 'admin' user

.. parsed-literal::

 ckan -c |ckan.ini| user remove admin


views: Create views on relevant resources
=========================================

Usage

.. parsed-literal::

 ckan views clean      - permanently delete views for all types no...
 ckan views clear      - permanently delete all views or the ones with...
 ckan views create     - create views on relevant resources.

 ckan views --dataset (-d)        - Set Dataset
 ckan views --no-default-filters
 ckan views --search (-s)         - Set Search
 ckan views --yes (-y)
