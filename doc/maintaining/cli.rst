.. _cli:

======================
Command Line Interface (CLI)
======================

NB: From CKAN 2.9 onwards the CKAN configuration file is named 'ckan.ini'. Previous names: 'production.ini' and 'development.ini' (plus others) may also still appear in documentation and the software. These legacy names will eventually be phased out. Also from CKAN 2.9 onwards, the ``paster`` command used for common CKAN administration tasks has been replaced with the  ``ckan`` command.

If you have trouble running ckan commands, see
`Troubleshooting ckan Commands`_ below.

.. note::

   Once you activate your CKAN virtualenv the "ckan" command is available from within any 
   location within the host environment.

   To run a ckan command without activating the virtualenv first, you have
   to give the full path the ckan script within the virtualenv, for example:

   .. parsed-literal::

      |virtualenv|/bin/ckan -c |/path/to/ckan.ini| user list 

   In the example commands below, we assume you're running the commands with
   your virtualenv activated and from your ckan directory.

The general form of a CKAN ``ckan`` command is:

.. parsed-literal::

   ckan --config=\ |/path/to/ckan.ini| **command** 

The `` --config`` option tells CKAN where to find your config file, which it
reads for example to know which database it should use. As you'll see in the
examples below, this option can be given as ``-c`` for short.

The config file (ckan.ini) will generally be located in the ``/etc/ckan/default/`` directory however it can be located in any directory on the host machine

``command`` should be replaced with the name of the CKAN command that you wish
to execute. Most commands have their own subcommands and options. 

.. note::

  You may also specify the location of your config file using the CKAN_INI
  environment variable. You will no longer need to use --config= or -c to
  tell ckan where the config file is:

  .. parsed-literal::

     export CKAN_INI=\ |/path/to/ckan.ini|
     
  You can still run the ckan command in the same directory as the CKAN config file when the config file is named 'development.ini'. You will not be required to use --config or -c in this case. However this usage is deprecated and will be phased out in a future CKAN release.
  
  .. parsed-literal::

     |cd /path/to/ckandir;| ckan command


.. parsed-literal::


Commands and Subcommands

   ckan -c |/path/to/ckan.ini| user list

(Here ``user`` is the name of the CKAN command you're running, and ``list`` is
a subcommand of ``user``.)

For a list of all available commands, you will need to access `CKAN Commands Reference`_. 

Each command has its own help text, which tells you what subcommands and
options it has (if any). To print out a command's help text, run the command
with the ``--help`` option::

   ckan -c |/path/to/ckan.ini| user --help


-------------------------------
Troubleshooting ckan Commands
-------------------------------

Permission Error
================

If you receive 'Permission Denied' error, try running ckan with sudo.

.. parsed-literal::

  sudo |virtualenv|/bin/ckan -c |/path/to/ckan.ini| db clean 

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
* **ImportError: No module named fanstatic** (or other ``ImportError``\ s)

Running ckan commands provided by extensions
==============================================

**If you're trying to run a CKAN command provided by an extension** that you've
installed and you're getting an error like **Command 'foo' not known** even
though you've activated your virtualenv and changed to the ckan directory, this
is because you need to run the extension's ckan commands from the extension's
source directory not CKAN's source directory. For example:

.. parsed-literal::

   |activate|
   cd |virtualenv|/src/ckanext-spatial
   ckan -c |/path/to/ckan.ini| foo 

This should not be necessary when using the pre-installed extensions that come
with CKAN.


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
config-tool       Tool for editing options in a CKAN config file
datapusher        Perform commands in the datapusher.
dataset           Manage datasets.
datastore         Perform commands to set up the datastore.
db                Perform various tasks on the database.
front-end-build   Creates and minifies css and JavaScript files
generate          Generate empty extension files to expand CKAN
jobs              Manage background jobs
less              Compile all root less documents into their CSS counterparts
minify            Create minified versions of the given Javascript and CSS files.
notify            Send out modification notifications.
plugin-info       Provide info on installed plugins.
profile           Code speed profiler
search-index      Creates a search index for all datasets
seed              Create test data in the database.
server            Start Development server.
sysadmin          Gives sysadmin rights to a named user.
tracking          Update tracking statistics.
translation       Translation helper functions
user              Manage users.
views             Create views on relevant resources
================= ============================================================


asset: WebAssets commands
==================================

Usage::

    ckan asset build            - Builds bundles, regardless of whether they are changed or not
    ckan asset watch            - Start a daemon which monitors source files, and rebuilds bundles
    ckan asset clean            - Will clear out the cache, which after a while can grow quite large


config-tool: Tool for editing options in a CKAN config file
==================================

Usage::

    ckan config-tool --section (-s)  - Section of the config file
    ckan config-tool --edit (-e)     - Checks the option already exists in the config file
    ckan config-tool --file (-f)     - Supply an options file to merge in

Examples::

      ckan config-tool |/path/to/ckan.ini| sqlalchemy.url=123 'ckan.site_title=ABC'
      ckan config-tool |/path/to/ckan.ini| -s server:main -e port=8080
      ckan config-tool |/path/to/ckan.ini| -f custom_options.ini


datapusher: Perform commands in the datapusher
==================================


dataset: Manage datasets
========================

Usage::

    ckan dataset DATASET_NAME|ID            - shows dataset properties
    ckan dataset show DATASET_NAME|ID       - shows dataset properties
    ckan dataset list                       - lists datasets
    ckan dataset delete [DATASET_NAME|ID]   - changes dataset state to 'deleted'
    ckan dataset purge [DATASET_NAME|ID]    - removes dataset from db entirely


datastore: Perform commands to set up the datastore
===================================================

Make sure that the datastore URLs are set properly before you run these commands.

Usage::

    ckan datastore set-permissions  - shows a SQL script to execute


db: Manage databases
====================

See :doc:`database-management`.


front-end-build: Creates and minifies css and JavaScript files
==============================================================

Usage::

    ckan front-end-build
    
    
generate: Generate empty extension files to expand CKANs
==============================================================

Usage::

    ckan generate --output-dir (-o)   -   Location to put the generated template  


.. _cli jobs:

jobs: Manage background jobs
============================

The ``jobs`` command can be used to manage :ref:`background jobs`.

.. versionadded:: 2.7


.. _cli jobs worker:

Run a background job worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs worker [--burst] [QUEUES]

Starts a worker that fetches job from the :ref:`job queues <background jobs
queues>` and executes them. If no queue names are given then it listens to
the default queue. This is equivalent to

::

    ckan -c |/path/to/ckan.ini| jobs worker default

If queue names are given then the worker listens to those queues and only
those::

    ckan -c |/path/to/ckan.ini| jobs worker my-custom-queue another-special-queue

Hence, if you want the worker to listen to the default queue and some others
then you must list the default queue explicitly::

    ckan -c |/path/to/ckan.ini| jobs worker default my-custom-queue

If the ``--burst`` option is given then the worker will exit as soon as all its
queues are empty. Otherwise it will wait indefinitely until a new job is
enqueued (this is the default).

.. note::

    In a production setting you should :ref:`use a more robust way of running
    background workers <background jobs supervisor>`.


.. _cli jobs list:

List enqueued jobs
^^^^^^^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs list [QUEUES]

Lists the currently enqueued jobs from the given :ref:`job queues <background
jobs queues>`. If no queue names are given then the jobs from all queues are
listed.


.. _cli jobs show:

Show details about a job
^^^^^^^^^^^^^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs show ID

Shows details about the enqueued job with the given ID.


.. _cli jobs cancel:

Cancel a job
^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs cancel ID

Cancels the enqueued job with the given ID. Jobs can only be canceled while
they are enqueued. Once a worker has started executing a job it cannot be
aborted anymore.


.. _cli jobs clear:

Clear job queues
^^^^^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs clear [QUEUES]

Cancels all jobs on the given :ref:`job queues <background jobs queues>`. If no
queues are given then *all* queues are cleared.


.. _cli jobs test:

Enqueue a test job
^^^^^^^^^^^^^^^^^^
::

    ckan -c |/path/to/ckan.ini| jobs test [QUEUES]

Enqueues a test job. If no :ref:`job queues <background jobs queues>` are given
then the job is added to the default queue. If queue names are given then a
separate test job is added to each of the queues.


.. _less:

less: Compile all root less documents into their CSS counterparts
=================================================================

Usage::

    less


minify: Create minified versions of the given Javascript and CSS files
======================================================================

Usage::

    ckan minify [--clean] PATH

    For example:

    ckan -c |/path/to/ckan.ini| minify ckan/public/base
    ckan -c |/path/to/ckan.ini| minify ckan/public/base/css/*.css
    ckan -c |/path/to/ckan.ini| minify ckan/public/base/css/red.css

If the --clean option is provided any minified files will be removed.


notify: Send out modification notifications
===========================================

Usage::

    ckan notify replay    - send out modification signals. In "replay" mode,
                       an update signal is sent for each dataset in the database.


plugin-info: Provide info on installed plugins
==============================================

As the name suggests, this commands shows you the installed plugins, their description, and which interfaces they implement


profile: Code speed profiler
============================

Provide a ckan url and it will make the request and record how long each function call took in a file that can be read
by runsnakerun.

Usage::

   ckan profile URL

The result is saved in profile.data.search. To view the profile in runsnakerun::

   runsnakerun ckan.data.search.profile

You may need to install the cProfile python module.


search-index: Search index commands
===============================

Usage::

    ckan search-index --verbose (-v)           - Verbose
    ckan search-index --force (-i)             - Ignore exceptions when rebuilding the index
    ckan search-index --refresh (-r)           - Ignore exceptions when rebuilding the index
    ckan search-index --only-missing (-o)      - Index non indexed datasets only
    ckan search-index --quiet (-q)             - Do not output index rebuild progress
    ckan search-index --commit-each (-e)       - Perform a commit after indexing each dataset
    

.. _rebuild search index:

search-index: Rebuild search index
==================================

Rebuilds the search index. This is useful to prevent search indexes from getting out of sync with the main database.

For example::

 ckan -c |/path/to/ckan.ini| search-index rebuild 

This default behaviour will clear the index and rebuild it with all datasets. If you want to rebuild it for only
one dataset, you can provide a dataset name::

    ckan -c |/path/to/ckan.ini| search-index rebuild test-dataset-name 

Alternatively, you can use the `-o` or `--only-missing` option to only reindex datasets which are not
already indexed::

    ckan -c |/path/to/ckan.ini| search-index rebuild -o 

If you don't want to rebuild the whole index, but just refresh it, use the `-r` or `--refresh` option. This
won't clear the index before starting rebuilding it::

    ckan -c |/path/to/ckan.ini| search-index rebuild -r 

There is also an option available which works like the refresh option but tries to use all processes on the
computer to reindex faster::

    ckan -c |/path/to/ckan.ini| search-index rebuild_fast 

There are other search related commands, mostly useful for debugging purposes::

    ckan search-index check                  - checks for datasets not indexed
    ckan search-index show DATASET_NAME      - shows index of a dataset
    ckan search-index clear [DATASET_NAME]   - clears the search index for the provided dataset or for the whole ckan instance


seed: Create test data in the database
==================================

Examples::

      ckan -c |/path/to/ckan.ini| seed 
      
      
server: Start Development server
==================================

Usage::

    ckan server --host (-h)          - Set Host
    ckan server --port (-p)          - Set Port
    ckan server --reloader (-r)      - Use reloader
    

sysadmin: Give sysadmin rights
==============================

Gives sysadmin rights to a named user. This means the user can perform any action on any object.

For example, to make a user called 'admin' into a sysadmin::

 ckan -c |/path/to/ckan.ini| sysadmin add admin 


tracking: Update tracking statistics
====================================

Usage::

    ckan tracking update [start_date]       - update tracking stats
    ckan tracking export FILE [start_date]  - export tracking stats to a csv file


translation: Translation helper functions
===================================

Usage::

    ckan translation js          - generate the JavaScript translations
    ckan translation mangle      - mangle the zh_TW translations for testing
    ckan translation check-po    - check po files for common mistakes

.. note::

    Since version 2.7 the JavaScript translation files are automatically
    regenerated if necessary when CKAN is started. Hence you usually do not
    need to run ``ckan trans js`` manually.


.. _cli-user:

user: Create and manage users
=============================

Lets you create, remove, list and manage users.

For example, to create a new user called 'admin'::

 ckan -c |/path/to/ckan.ini| user add admin 

To delete the 'admin' user::

 ckan -c |/path/to/ckan.ini| user remove admin 
 

views: Create views on relevant resources
=============================

Usage::

    ckan views --dataset (-d)        - Set Dataset
    ckan views --no-default-filters
    ckan views --search (-s)         - Set Search
    ckan views --yes (-y)
