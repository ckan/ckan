.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/ckan/ckanext-xloader.svg?branch=master
    :target: https://travis-ci.org/ckan/ckanext-xloader

.. image:: https://img.shields.io/pypi/v/ckanext-xloader.svg
    :target: https://pypi.org/project/ckanext-xloader/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/ckanext-xloader.svg
    :target: https://pypi.org/project/ckanext-xloader/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/status/ckanext-xloader.svg
    :target: https://pypi.org/project/ckanext-xloader/
    :alt: Development Status

.. image:: https://img.shields.io/pypi/l/ckanext-xloader.svg
    :target: https://pypi.org/project/ckanext-xloader/
    :alt: License

=========================
XLoader - ckanext-xloader
=========================

Loads CSV (and similar) data into CKAN's DataStore. Designed as a replacement
for DataPusher because it offers ten times the speed and more robustness
(hence the name, derived from "Express Loader")

**OpenGov Inc.** has sponsored this development, with the aim of benefitting
open data infrastructure worldwide.

-------------------------------
Key differences from DataPusher
-------------------------------

Speed of loading
----------------

DataPusher - parses CSV rows, converts to detected column types, converts the
data to a JSON string, calls datastore_create for each batch of rows, which
reformats the data into an INSERT statement string, which is passed to
PostgreSQL.

XLoader - pipes the CSV file directly into PostgreSQL using COPY.

In `tests <https://github.com/ckan/ckanext-xloader/issues/25>`_, XLoader
is over ten times faster than DataPusher.

Robustness
----------

DataPusher - one cause of failure was when casting cells to a guessed type. The
type of a column was decided by looking at the values of only the first few
rows. So if a column is mainly numeric or dates, but a string (like "N/A")
comes later on, then this will cause the load to error at that point, leaving
it half-loaded into DataStore.

XLoader - loads all the cells as text, before allowing the admin to
convert columns to the types they want (using the Data Dictionary feature). In
future it could do automatic detection and conversion.

Simpler queueing tech
---------------------

DataPusher - job queue is done by ckan-service-provider which is bespoke,
complicated and stores jobs in its own database (sqlite by default).

XLoader - job queue is done by RQ, which is simpler, is backed by Redis, allows
access to the CKAN model and is CKAN's default queue technology.
You can also debug jobs easily using pdb. Job results are stored in
Sqlite by default, and for production simply specify CKAN's database in the
config and it's held there - easy.

(The other obvious candidate is Celery, but we don't need its heavyweight
architecture and its jobs are not debuggable with pdb.)

Separate web server
-------------------

DataPusher - has the complication that the queue jobs are done by a separate
(Flask) web app, apart from CKAN. This was the design because the job requires
intensive processing to convert every line of the data into JSON. However it
means more complicated code as info needs to be passed between the services in
http requests, more for the user to set-up and manage - another app config,
another apache config, separate log files.

XLoader - the job runs in a worker process, in the same app as CKAN, so
can access the CKAN config, db and logging directly and avoids many HTTP calls.
This simplification makes sense because the xloader job doesn't need to do much
processing - mainly it is streaming the CSV file from disk into PostgreSQL.

It is still entirely possible to run the XLoader worker on a separate server,
if that is desired. The worker needs the following:

- A copy of CKAN installed in the same Python virtualenv (but not running).
- A copy of the CKAN config file.
- Access to the Redis instance that the running CKAN app uses to store jobs.
- Access to the database.

You can then run it via `ckan jobs worker` as below.

Caveat - column types
---------------------

Note: With XLoader, all columns are stored in DataStore's database as 'text'
type (whereas DataPusher did some rudimentary type guessing - see 'Robustness'
above). However once a resource is xloaded, an admin can use the resource's
Data Dictionary tab to change these types to numeric or
datestamp and re-load the file. When migrating from DataPusher to XLoader you
can preserve the types of existing resources by using the ``migrate_types``
command.

There is scope to add functionality for automatically guessing column type -
offers to contribute this are welcomed.


------------
Requirements
------------

Compatibility with core CKAN versions:

=============== =============
CKAN version    Compatibility
=============== =============
2.7             no longer supported (last supported version: 0.12.2)
2.8             no longer supported (last supported version: 0.12.2)
2.9             yes (Python3) (last supported version for Python 2.7: 0.12.2)), Must: ``pip install "setuptools>=44.1.0,<71"``
2.10            yes
2.11            yes
=============== =============

------------
Installation
------------

To install XLoader:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-xloader Python package into your virtual environment::

     pip install ckanext-xloader

3. Install dependencies::

     pip install -r https://raw.githubusercontent.com/ckan/ckanext-xloader/master/requirements.txt
     pip install -U requests[security]

4. Add ``xloader`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

   You should also remove ``datapusher`` if it is in the list, to avoid them
   both trying to load resources into the DataStore.

   Ensure ``datastore`` is also listed, to enable CKAN DataStore.

5. Starting CKAN 2.10 you will need to set an API Token to be able to
   execute jobs against the server::

     ckanext.xloader.api_token = <your-CKAN-generated-API-Token>

6. If it is a production server, you'll want to store jobs info in a more
   robust database than the default sqlite file. It can happily use the main
   CKAN postgres db by adding this line to the config, but with the same value
   as you have for ``sqlalchemy.url``::

     ckanext.xloader.jobs_db.uri = postgresql://ckan_default:pass@localhost/ckan_default

   (This step can be skipped when just developing or testing.)

7. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

8. Run the worker::

    ckan -c /etc/ckan/default/ckan.ini jobs worker


---------------
Config settings
---------------

Configuration:

See the extension's `config_declaration.yaml <ckanext/xloader/config_declaration.yaml>`_ file.

This plugin also supports the `ckan.download_proxy` setting, to use a proxy server when downloading files.
This setting is shared with other plugins that download resource files, such as ckanext-archiver. Eg:

    ckan.download_proxy = http://my-proxy:1234/

You may also wish to configure the database to use your preferred date input style on COPY.
For example, to make [PostgreSQL](https://www.postgresql.org/docs/current/runtime-config-client.html#RUNTIME-CONFIG-CLIENT-FORMAT)
expect European (day-first) dates, you could add to ``postgresql.conf``:

    datestyle=ISO,DMY

External Database credentials for datastore

     ``ckanext.xloader.jobs_db.uri = postgresql://ckan_default:pass@localhost/ckan_default``

API Key requires for xloader interaction CKAN 2.10 onwards, to generate  ``TOKEN=ckan -c /etc/ckan/default/production.ini user token add $ACCOUNT xloader | tail -1 | tr -d '[:space:]')``

     ``ckanext.xloader.api_token = <your-CKAN-generated-API-Token>``

Badge notification on what xloader is doing

     ``ckanext.xloader.show_badges = True|False (default True)``

     ``ckanext.xloader.debug_badges = True|False (default False)``

------------------------
Developer installation
------------------------

To install XLoader for development, activate your CKAN virtualenv and
in the directory up from your local ckan repo::

    git clone https://github.com/ckan/ckanext-xloader.git
    cd ckanext-xloader
    pip install -e .
    pip install -r requirements.txt
    pip install -r dev-requirements.txt


-------------------------
Upgrading from DataPusher
-------------------------

To upgrade from DataPusher to XLoader:

1. Install XLoader as above, including running the xloader worker.

2. (Optional) For existing datasets that have been datapushed to datastore, freeze the column types (in the data dictionaries), so that XLoader doesn't change them back to string on next xload::

       ckan -c /etc/ckan/default/ckan.ini migrate_types

3. If you've not already, change the enabled plugin in your config - on the
   ``ckan.plugins`` line replace ``datapusher`` with ``xloader``.

4. (Optional) If you wish, you can disable the direct loading and continue to
   just use tabulator - for more about this see the docs on config option:
   ``ckanext.xloader.use_type_guessing``

5. Stop the datapusher worker::

       sudo a2dissite datapusher

6. Restart CKAN::

       sudo service apache2 reload
       sudo service nginx reload

----------------------
Command-line interface
----------------------

You can submit single or multiple resources to be xloaded using the
command-line interface.

e.g. ::

    ckan -c /etc/ckan/default/ckan.ini xloader submit <dataset-name>

For debugging you can try xloading it synchronously (which does the load
directly, rather than asking the worker to do it) with the ``-s`` option::

    ckan -c /etc/ckan/default/ckan.ini xloader submit <dataset-name> -s

See the status of jobs::

    ckan -c /etc/ckan/default/ckan.ini xloader status

Submit all datasets' resources to the DataStore::

    ckan -c /etc/ckan/default/ckan.ini xloader submit all

Re-submit all the resources already in the DataStore (Ignores any resources
that have not been stored in DataStore e.g. because they are not tabular)::

    ckan -c /etc/ckan/default/ckan.ini xloader submit all-existing


**Full list of XLoader CLI commands**::

    ckan -c /etc/ckan/default/ckan.ini xloader --help


Jobs and workers
----------------

Main docs for managing jobs: <https://docs.ckan.org/en/latest/maintaining/background-tasks.html#managing-background-jobs>

Main docs for running and managing workers are here: https://docs.ckan.org/en/latest/maintaining/background-tasks.html#running-background-jobs

Useful commands:

Clear (delete) all outstanding jobs::

    ckan -c /etc/ckan/default/ckan.ini jobs clear [QUEUES]

If having trouble with the worker process, restarting it can help::

    sudo supervisorctl restart ckan-worker:*

---------------
Troubleshooting
---------------

**KeyError: "Action 'datastore_search' not found"**

You need to enable the `datastore` plugin in your CKAN config. See
'Installation' section above to do this and restart the worker.

**ProgrammingError: (ProgrammingError) relation "_table_metadata" does not
exist**

Your DataStore permissions have not been set-up - see:
<https://docs.ckan.org/en/latest/maintaining/datastore.html#set-permissions>

-----------------
Running the Tests
-----------------

The first time, your test datastore database needs the trigger applied::

    sudo -u postgres psql datastore_test -f full_text_function.sql

To run the tests, do::

    pytest ckan-ini=test.ini ckanext/xloader/tests


----------------------------------
Releasing a New Version of XLoader
----------------------------------

XLoader is available on PyPI as https://pypi.org/project/ckanext-xloader.

To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Update the CHANGELOG.

3. Make sure you have the latest version of necessary packages::

       pip install --upgrade setuptools wheel twine

4. Create source and binary distributions of the new version::

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

5. Upload the source distribution to PyPI::

       twine upload dist/*

6. Commit any outstanding changes::

       git commit -a
       git push

7. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags
