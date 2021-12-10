.. include:: ../_substitutions.rst

=====================
Configuration Options
=====================

The functionality and features of CKAN can be modified using many different
configuration options. These are generally set in the `CKAN configuration file`_,
but some of them can also be set via `Environment variables`_ or at :ref:`runtime <runtime-config>`.
Config options can be :ref:`declared on strict mode <declare-config-options>` to ensure they are validated and have default values.

.. note:: Looking for the available configuration options? Jump to `CKAN configuration file`_.




Environment variables
*********************

Some of the CKAN configuration options can be defined as `Environment variables`_
on the server operating system.

These are generally low-level critical settings needed when setting up the application, like the database
connection, the Solr server URL, etc. Sometimes it can be useful to define them as environment variables to
automate and orchestrate deployments without having to first modify the `CKAN configuration file`_.

These options are only read at startup time to update the ``config`` object used by CKAN,
but they won't be accessed any more during the lifetime of the application.

CKAN environment variable names match the options in the configuration file, but they are always uppercase
and prefixed with `CKAN_` (this prefix is added even if
the corresponding option in the ini file does not have it), and replacing dots with underscores.

This is the list of currently supported environment variables, please refer to the entries in the
`CKAN configuration file`_ section below for more details about each one:

.. literalinclude:: /../ckan/config/environment.py
    :language: python
    :start-after: Start CONFIG_FROM_ENV_VARS
    :end-before: End CONFIG_FROM_ENV_VARS

.. _Environment variables: http://en.wikipedia.org/wiki/Environment_variable


.. _runtime-config:

Updating configuration options during runtime
*********************************************

CKAN configuration options are generally defined before starting the web application (either in the
`CKAN configuration file`_ or via `Environment variables`_).

A limited number of configuration options can also be edited during runtime. This can be done on the
:ref:`administration interface <admin page>` or using the :py:func:`~ckan.logic.action.update.config_option_update`
API action. Only :doc:`sysadmins </sysadmin-guide>` can edit these runtime-editable configuration options. Changes made to these configuration options will be stored in the database and persisted when the server is restarted.

Extensions can add (or remove) configuration options to the ones that can be edited at runtime. For more
details on how to do this check :doc:`/extensions/remote-config-update`.

.. _declare-config-options:

Config declaration
******************

Tracking down all the possible config options in your CKAN site can be a
challenging task. CKAN itself and its extensions change over time, deprecating
features and providing new ones, which means that some new config options may be
introduced, while other options no longer have any effect. In
order to keep track of all valid config options, CKAN uses config declarations.

CKAN itself declares all the config options that are used throught the
code base (You can see the core config declarations in
the ``ckan/config/config_declaration.yaml`` file). This allows to validate the
current configuration against the declaration, or check which config
options in the CKAN config file are not declared (and might have no effect).

.. note:: To make use of the config declaration feature you need to set :ref:`config.mode` to ``strict``

Declaring config options
------------------------

The :py:class:`~ckan.plugins.interfaces.IConfigDeclaration` interface is
available to allow extensions to declare their own config options.

New config options can only be declared inside the
:py:meth:`~ckan.plugins.interfaces.IConfigDeclaration.declare_config_options` method. This
method accepts two arguments: a :py:class:`~ckan.config.declaration.Declaration`
object that contains all the declarations, and a :py:class:`~ckan.config.declaration.Key`
helper, which allows to declare more unusual config options.

A very basic config option may be declared in this way::

  declaration.declare("ckanext.my_ext.option")

which just means that extension ``my_ext`` makes use of a config option named
``ckanext.my_ext.option``. If we want to define the *default value* for this option
we can write::

  declaration.declare("ckanext.my_ext.option", True)

The second parameter to
:py:meth:`~ckan.config.declaration.Declaration.declare` specifies the default
value of the declared option if it is not provided in the configuration file.
If a default value is not specified, it's implicitly set to ``None``.

You can assign validators to a declared config option::

  option = declaration.declare("ckanext.my_ext.option", True)
  option.set_validators("not_missing boolean_validator")

``set_validators`` accepts a string with the names of validators that must be applied to the config option.
These validators need to registered in CKAN core or in your own extension using
the :py:class:`~ckan.plugins.interfaces.IValidators` interface.

.. note:: Declared default values are also passed to validators. In addition,
          different validators can be applied to the same option. This means that
          validators must be idempotent and that the efault value itself must be valid for
          the given set of validators.

If this is a mandatory option (ie users need to explicitly provide a value and can't
rely on a default value)::

    option.required()

If you need to declare a lot of options, you can declare all of them at once loading a dict::

  declaration.load_dict(DICT_WITH_DECLARATIONS)

This allows to keep the configuration declaration in a separate file to make it easier to maintain if
your plugin supports several config options.

.. note:: ``declaration.load_dict()`` takes only python dictionary as argument. If
          you store the declaration in an external file like a JSON, YAML file, you have to parse it into a
          Python dictionary yourself.

Accessing config options
------------------------

Using validators ensures that config values are normalized. Up until now you have probably seen
code like this one::

  is_enabled = toolkit.asbool(toolkit.config.get("ckanext.my_ext.enable", False))

Declaring this configuration option and assigning validators (`convert_int`,
`boolean_validators`) and a default value means that we can use the ``config.get_value()`` method::

  is_enabled = toolkit.config.get_value("ckanext.my_ext.enable")

This will ensure that:

 1. If the value is not explicitly defined in the configuration file, the default one will be picked
 2. This value is passed to the validators, and a valid value is returned


.. note:: An attempt to use ``config.get_value()`` with an undeclared config option
          will print a warning to the logs and return the option value or ``None`` as default.


Command line interface
----------------------

The current configuration can be validated using the :ref:`config declaration CLI <cli.ckan.config>` (again, assuming that
you have set :ref:`config.mode` to ``strict``)::

  ckan config validate

To get an example of the configuration for a given plugin, run ``ckan
config declaration <PLUGIN>``, eg::

  ckan config declaration datastore

  ## Datastore settings ##########################################################
  ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default
  ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default
  ckan.datastore.sqlsearch.enabled = false
  ckan.datastore.search.rows_default = 100
  ckan.datastore.search.rows_max = 32000
  # ckan.datastore.sqlalchemy.<OPTION> =

  ## PostgreSQL' full-text search parameters #####################################
  ckan.datastore.default_fts_lang = english
  ckan.datastore.default_fts_index_method = gist


To get an example of the declaration code itself in order to use it as a starting point in your own plugin, you can
run ``ckan config describe <PLUGIN>``, eg::

  ckan config describe datapusher

  # Output:
  declaration.annotate('Datapusher settings')
  declaration.declare(key.ckan.datapusher.formats, ...)
  declaration.declare(key.ckan.datapusher.url)
  declaration.declare(key.ckan.datapusher.callback_url_base)
  declaration.declare(key.ckan.datapusher.assume_task_stale_after, 3600).set_validators('convert_int')

You can output the config declaration in different formats, which is useful if you want to keep
them separately::

  ckan config describe datapusher --format=dict # python dict
  ckan config describe datapusher --format=json # JSON file
  ckan config describe datapusher --format=yaml # YAML file
  ckan config describe datapusher --format=toml # TOML file



.. _config_file:

CKAN configuration file
***********************

From CKAN 2.9, by default, the configuration file is located at
``/etc/ckan/default/ckan.ini``. Previous releases the configuration file(s)
were:  ``/etc/ckan/default/development.ini`` or
``/etc/ckan/default/production.ini``. This section documents all of the config
file settings, for reference.

.. note:: After editing your config file, you need to restart your webserver
   for the changes to take effect.

.. note:: Unless otherwise noted, all configuration options should be set inside
   the ``[app:main]`` section of the config file (i.e. after the ``[app:main]``
   line)::

        [DEFAULT]

        ...

        [server:main]
        use = egg:Paste#http
        host = 0.0.0.0
        port = 5000

        # This setting will not work, because it's outside of [app:main].
        ckan.site_logo = /images/masaq.png

        [app:main]
        # This setting will work.
        ckan.plugins = stats text_view recline_view

   If the same option is set more than once in your config file, exeption will
   be raised and CKAN application will not start


.. warning:: hello

.. include:: ../_config_options.rst

.. warning:: world


.. start_config-datastore-urls

.. _ckan.datastore.write_url:

ckan.datastore.write_url
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.write_url = postgresql://ckanuser:pass@localhost/datastore

The database connection to use for writing to the datastore (this can be
ignored if you're not using the :doc:`datastore`). Note that the database used
should not be the same as the normal CKAN database. The format is the same as
in :ref:`sqlalchemy.url`.

.. _ckan.datastore.read_url:

ckan.datastore.read_url
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.read_url = postgresql://readonlyuser:pass@localhost/datastore

The database connection to use for reading from the datastore (this can be
ignored if you're not using the :doc:`datastore`). The database used must be
the same used in :ref:`ckan.datastore.write_url`, but the user should be one
with read permissions only. The format is the same as in :ref:`sqlalchemy.url`.

.. end_config-datastore-urls

.. _ckan.datastore.sqlalchemy:

ckan.datastore.sqlalchemy.*
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.sqlalchemy.pool_size=10
 ckan.datastore.sqlalchemy.max_overflow=20

Custom sqlalchemy config parameters used to establish the DataStore
database connection.

To get the list of all the available properties check the `SQLAlchemy documentation`_

.. _SQLAlchemy documentation: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#engine-creation-api

.. _ckan.datastore.default_fts_lang:

ckan.datastore.default_fts_lang
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.default_fts_lang = english

Default value: |config:ckan.datastore.default_fts_lang|

This can be ignored if you're not using the :doc:`datastore`.

The default language used when creating full-text search indexes and querying
them. It can be overwritten by the user by passing the "lang" parameter to
"datastore_search" and "datastore_create".

.. _ckan.datastore.default_fts_index_method:

ckan.datastore.default_fts_index_method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.default_fts_index_method = gist

Default value: |config:ckan.datastore.default_fts_index_method|

This can be ignored if you're not using the :doc:`datastore`.

The default method used when creating full-text search indexes. Currently it
can be "gin" or "gist". Refer to PostgreSQL's documentation to understand the
characteristics of each one and pick the best for your instance.

.. _ckan.datastore.sqlsearch.enabled:

ckan.datastore.sqlsearch.enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.sqlsearch.enabled = True

Default value: |config:ckan.datastore.sqlsearch.enabled|

This option allows you to enable the :py:func:`~ckanext.datastore.logic.action.datastore_search_sql` action function, and corresponding API endpoint.

This action function has protections from abuse including:

- parsing of the query to prevent unsafe functions from being called, see :ref:`ckan.datastore.sqlsearch.allowed_functions_file`
- parsing of the query to prevent multiple statements
- prevention of data modification by using a read-only database role
- use of ``explain`` to resolve tables accessed in the query to check against user permissions
- use of a statement timeout to prevent queries from running indefinitely

These protections offer some safety but are not designed to prevent all types of abuse. Depending on the sensitivity of private data in your datastore and the likelihood of abuse of your site you may choose to disable this action function or restrict its use with a :py:class:`~ckan.plugins.interfaces.IAuthFunctions` plugin.

.. _ckan.datastore.search.rows_default:

ckan.datastore.search.rows_default
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.search.rows_default = 1000

Default value: |config:ckan.datastore.search.rows_default|

Default number of rows returned by ``datastore_search``, unless the client
specifies a different ``limit`` (up to ``ckan.datastore.search.rows_max``).

NB this setting does not affect ``datastore_search_sql``.

.. _ckan.datastore.search.rows_max:

ckan.datastore.search.rows_max
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.search.rows_max = 1000000

Default value: |config:ckan.datastore.search.rows_max|

Maximum allowed value for the number of rows returned by the datastore.

Specifically this limits:

* ``datastore_search``'s ``limit`` parameter.
* ``datastore_search_sql`` queries have this limit inserted.

.. _ckan.datastore.sqlsearch.allowed_functions_file:

ckan.datastore.sqlsearch.allowed_functions_file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.sqlsearch.allowed_functions_file = /path/to/my_allowed_functions.txt

Default value: File included in the source code at |config:ckan.datastore.sqlsearch.allowed_functions_file|.

Allows to define the path to a text file listing the SQL functions that should be allowed to run
on queries sent to the :py:func:`~ckanext.datastore.logic.action.datastore_search_sql` function
(if enabled, see :ref:`ckan.datastore.sqlsearch.enabled`). Function names should be listed one on
each line, eg::

    abbrev
    abs
    abstime
    ...





.. _config-authorization:

Authorization Settings
----------------------

More information about how authorization works in CKAN can be found the
:doc:`authorization` section.

.. start_config-authorization

.. _ckan.auth.anon_create_dataset:

...

ckan.auth.create_default_api_keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. end_config-authorization



CORS Settings
-------------

Cross-Origin Resource Sharing (CORS) can be enabled and controlled with the following settings:






.. _ckan.resource_proxy.max_file_size:

ckan.resource_proxy.max_file_size
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.resource_proxy.max_file_size = 1048576

Default value: |config:ckan.resource_proxy.max_file_size|

This sets the upper file size limit for in-line previews.
Increasing the value allows CKAN to preview larger files (e.g. PDFs) in-line;
however, a higher value might cause time-outs, or unresponsive browsers for CKAN users
with lower bandwidth. If left commented out, CKAN will default to 1 MB.


.. _ckan.resource_proxy.chunk_size:

ckan.resource_proxy.chunk_size
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.resource_proxy.chunk_size = 8192

Default value: |config:ckan.resource_proxy.chunk_size|

This sets size of the chunk to read and write when proxying.
Raising this value might save some CPU cycles. It makes no sense to lower it
below the page size, which is default.


.. _ckan.preview.json_formats:

ckan.preview.json_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.json_formats = json

Default value: |config:ckan.preview.json_formats|

Space-delimited list of JSON based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.xml_formats:

ckan.preview.xml_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.xml_formats = xml rdf rss

Default value: |config:ckan.preview.xml_formats|

Space-delimited list of XML based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.text_formats:

ckan.preview.text_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.text_formats = txt plain

Default value: |config:ckan.preview.text_formats|

Space-delimited list of plain text based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.image_formats:

ckan.preview.image_formats
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.image_formats = png jpeg jpg gif

Default value: |config:ckan.preview.image_formats|

Space-delimited list of image-based resource formats that will be rendered by the Image view plugin (``image_view``)


.. _ckan.recline.dataproxy_url:

ckan.recline.dataproxy_url
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.recline.dataproxy_url = https://mydataproxy.example.com

Default value: |config:ckan.recline.dataproxy_url|

Custom URL to a self-hosted DataProxy instance. The DataProxy is an external service currently used to stream data in
JSON format to the Recline-based views when data is not on the DataStore. The main instance is deprecated and will
be eventually shut down, so users that require it can host an instance themselves and use this configuration option
to point Recline to it.


.. _ckan.datatables.page_length_choices:

ckan.datatables.page_length_choices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.page_length_choices = 20 50 100 500 1000 5000

Default value: |config:ckan.datatables.page_length_choices|

Space-delimited list of the choices for the number of rows per page, with the lowest value being the default initial value.

.. note:: On larger screens, DataTables view will attempt to fill the table with as many rows that can fit using the lowest closest choice.

.. _ckan.datatables.state_saving:

ckan.datatables.state_saving
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.state_saving = False

Default value: |config:ckan.datatables.state_saving|

Enable or disable state saving. When enabled, DataTables view will store state information such as pagination position,
page length, row selection/s, column visibility/ordering, filtering and sorting using the browser's localStorage.
When the end user reloads the page, the table's state will be altered to match what they had previously set up.

This also enables/disables the "Reset" and "Share current view" buttons. "Reset" discards the saved state. "Share current view" base-64 encodes
the state and passes it as a url parameter, acting like a "saved search" that can be used for embedding and sharing table searches.

.. _ckan.datatables.state_duration:

ckan.datatables.state_duration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.state_duration = 86400

Default value: |config:ckan.datatables.state_duration|

Duration (in seconds) for which the saved state information is considered valid. After this period has elapsed, the table's state will
be returned to the default, and the state cleared from the browser's localStorage.

.. note:: The value ``0`` is a special value as it indicates that the state can be stored and retrieved indefinitely with no time limit.

.. _ckan.datatables.data_dictionary_labels:

ckan.datatables.data_dictionary_labels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.data_dictionary_labels = True

Default value: |config:ckan.datatables.data_dictionary_labels|

Enable or disable data dictionary integration. When enabled, a column's data dictionary label will be used in the table header. A tooltip for each
column with data dictionary information will also be integrated into the header.

.. _ckan.datatables.ellipsis_length:

ckan.datatables.ellipsis_length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.ellipsis_length = 100

Default value: |config:ckan.datatables.ellipsis_length|

The maximum number of characters to show in a cell before it is truncated. An ellipsis (...) will be added at the truncation point and the
full text of the cell will be available as a tooltip. This value can be overridden at the resource level when configuring a DataTables resource view.

.. note:: The value ``0`` is a special value as it indicates that the column's width will be determined by the column name, and cell content will word-wrap.

.. _ckan.datatables.date_format:

ckan.datatables.date_format
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.date_format = YYYY-MM-DD dd ww

Default value: |config:ckan.datatables.date_format|

The `moment.js date format
<https://momentjscom.readthedocs.io/en/latest/moment/04-displaying/01-format/>`_ to use to convert raw timestamps to a user-friendly date format using CKAN's current
locale language code. This value can be overridden at the resource level when configuring a DataTables resource view.

.. note:: The value ``NONE`` is a special value as it indicates that no date formatting will be applied and the raw ISO-8601 timestamp will be displayed.

.. _ckan.datatables.default_view:

ckan.datatables.default_view
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datatables.default_view = list

Default value: |config:ckan.datatables.default_view|

Indicates the default view mode of the DataTable (valid values: ``table`` or ``list``). Table view is the typical grid layout, with horizontal scrolling.
List view is a responsive table, automatically hiding columns as required to fit the browser viewport. In addition, list view allows the user to view, copy and print
the details of a specific row. This value can be overridden at the resource level when configuring a DataTables resource view.

.. end_resource-views


DataPusher Settings
-------------------

.. _ckan.datapusher.formats:

ckan.datapusher.formats
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.formats = csv xls

Default value: |config:ckan.datapusher.formats|

File formats that will be pushed to the DataStore by the DataPusher. When
adding or editing a resource which links to a file in one of these formats,
the DataPusher will automatically try to import its contents to the DataStore.


.. _ckan.datapusher.url:

ckan.datapusher.url
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.url = http://127.0.0.1:8800/

DataPusher endpoint to use when enabling the ``datapusher`` extension. If you
installed CKAN via :doc:`/maintaining/installing/install-from-package`, the DataPusher was installed for you
running on port 8800. If you want to manually install the DataPusher, follow
the installation `instructions <http://docs.ckan.org/projects/datapusher>`_.


.. _ckan.datapusher.callback_url_base:

ckan.datapusher.callback_url_base
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.callback_url_base = http://ckan:5000/

Default value: Value of ``ckan.site_url``

Alternative callback URL for DataPusher when performing a request to CKAN. This is
useful on scenarios where the host where DataPusher is running can not access the
public CKAN site URL.


.. _ckan.datapusher.assume_task_stale_after:

ckan.datapusher.assume_task_stale_after
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.assume_task_stale_after = 86400

Default value: |config:ckan.datapusher.assume_task_stale_after|

In case a DataPusher task gets stuck and fails to recover, this is the minimum
amount of time (in seconds) after a resource is submitted to DataPusher that the
resource can be submitted again.
