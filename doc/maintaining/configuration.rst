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



.. include:: ../_config_options.inc
