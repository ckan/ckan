.. include:: ../_substitutions.rst

=====================
Configuration Options
=====================

The functionality and features of CKAN can be modified using many different
configuration options. These are generally set in the `CKAN configuration file`_,
but some of them can also be set via `Environment variables`_ or at :ref:`runtime <runtime-config>`.

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
          different validators can be applied to the same option multiple
          times. This means that validators must be idempotent and that the
          default value itself must be valid for the given set of validators.

If you need to declare a lot of options, you can declare all of them at once loading a dict::

  declaration.load_dict(DICT_WITH_DECLARATIONS)

This allows to keep the configuration declaration in a separate file to make it easier to maintain if
your plugin supports several config options.

.. note:: ``declaration.load_dict()`` takes only python dictionary as
          argument. If you store the declaration in an external file like a
          JSON, YAML file, you have to parse it into a Python dictionary
          yourself or use corresponding
          :py:attr:`~ckan.plugins.toolkit.ckan.plugins.toolkit.blanket`. Read
          the following section for additional information.

Use a blanket implementation of the config declaration
------------------------------------------------------

The recommended way of declaring config options is using the
``config_declarations``
:py:attr:`~ckan.plugins.toolkit.ckan.plugins.toolkit.blanket`. It allows you to
write less code and define your config options using JSON, YAML, or TOML (if the ``toml``
package is installed inside your virtual environment). That is how CKAN
declares config options for all its built-in plugins, like ``datastore`` or
``datatables_view``.

Instead of implementing the
:py:class:`~ckan.plugins.interfaces.IConfigDeclaration` interface, decorate the
plugin with the ``config_declarations`` blanket::

  import ckan.plugins as p
  import ckan.plugins.toolkit as tk

  @tk.blanket.config_declarations
  class MyExt(p.SingletonPlugin):
      pass

Next, create a file `config_declaration.yaml` at the root directory of your
extension: ``ckanext/my_ext/config_declaration.yaml``. You can use the `.json`
or `.toml` extension instead of `.yaml`.

Here is an example of the config declaration file. All the comments are added
only for explanation and you don't need them in the real file::


    # schema version of the config declaration. At the moment, the only valid value is `1`
    version: 1

    # an array of configuration blocks. Each block has an "annotation", that
    # describes the block, and the list of options. These groups help to separate
    # config options visually, but they have no extra meaning.
    groups:

    # short text that describes the group. It can be shown in the config file
    # as following:
    #   ## MyExt settings ##################
    #   some.option = some.value
    #   another.option = another.value
    - annotation: MyExt settings

      # an array of actual declarations
      options:

        # The only required item in the declaration is `key`. `key` defines the
        # name of the config option
        - key: my_ext.flag.do_something

          # default value, used when the option is missing from the config file.
          default: false

          # import path of the function that must be called in order to get the
          # default value. This can be used when the default value can be obtained from
          # an environment variable, database or any other external source.
          # IMPORTANT: use either `default` or `default_callable`, not both at the same time
          default_callable: ckanext.my_ext.utils:function_that_returns_default

          # Example of value that can be used for given option. If the config
          # option is missing from the config file, `placeholder` IS IGNORED. It
          # has only demonstration purpose. Good uses of `placeholder` are:
          # examples of secrets, examples of DB connection string.
          # IMPORTANT: do not use `default` and `placeholder` at the same
          # time. `placeholder` should be used INSTEAD OF the `default`
          # whenever you think it has a sense.
          placeholder: false

          # import path of the function that must be called in order to get the
          # placeholder value.  Basically, same as `default_callable`, but it
          # produces the value of `placeholder`.
          # IMPORTANT: use either `placeholder` or `placeholder_callable`, not both at the same time
          placeholder_callable: ckanext.my_ext.utils:function_that_returns_placeholder

          # A dictionary with keyword-arguments that will be passed to
          # `default_callable` or `placeholder_callable`.  As mentioned above,
          # only one of these options may be used at the same time, so
          # `callable_args` can be used by any of these options without a conflict.
          callable_args:
            arg_1: 20
            arg_2: "hello"

          # an alternative example of a valid value for option. Used only in
          # CKAN documentation, thus has no value for extensions.
          example: some-valid-value

          # an explanation of the effect that option has. Don't hesistate to
          # put as much details here as possible
          description: |
              Nullam eu ante vel est convallis dignissim.  Fusce suscipit, wisi
              nec facilisis facilisis, est dui fermentum leo, quis tempor
              ligula erat quis odio.  Nunc porta vulputate tellus.  Nunc rutrum
              turpis sed pede.  Sed bibendum.  Aliquam posuere.  Nunc aliquet,
              augue nec adipiscing interdum, lacus tellus malesuada massa, quis
              varius mi purus non odio.  Pellentesque condimentum, magna ut
              suscipit hendrerit, ipsum augue ornare nulla, non luctus diam
              neque sit amet urna.  Curabitur vulputate vestibulum lorem.
              Fusce sagittis, libero non molestie mollis, magna orci ultrices
              dolor, at vulputate neque nulla lacinia eros.  Sed id ligula quis
              est convallis tempor.  Curabitur lacinia pulvinar nibh.  Nam a
              sapien.

          # a space-separated list of validators, applied to the value of option.
          validators: not_missing boolean_validator

          # shortcut for the most common option types. It adds type validators to the option.
          # If both, `type` and `validators` are set, validators from `type` are added first,
          # then validators from `validators` are appended.
          # Valid types are: bool, int, list, dynamic (see below for more information on dynamic
          # options)
          type: bool

          # boolean flag that marks config option as experimental. Such options are hidden from
          # examples of configuration or any other auto-generated output. But they are declared,
          # thus can be validated and do not produce undeclared-warning. Use it for options that
          # are not stable and may be removed from your extension before the public release
          experimental: true

          # boolean flag that marks config option as ignored. Can be used for options that are set
          # programmatically. This flag means that there is no sense in setting this option, because
          # it will be overriden or won't be used at all.
          ignored: true

          # boolean flag that marks config option as hidden. Used for options that should not be set
          # inside config file or anyhow used by others. Often this flag is used for options
          # that are added by Flask core or its extensions.
          internal: true

          # boolean flag that marks config option as required. Doesn't have a special effect for now,
          # but may prevent application from startup in future, so use it only on options that
          # are essential for your plugin and that have no sensible default value.
          required: true

          # boolean flag that marks config option as editable. Doesn't have a special effect for now.
          # It's recommended to enable this flag for options that are editable via AdminUI.
          editable: true

          # boolean flag that marks option as commented. Such options are added
          # as comments to the config file generated from template.
          commented: true

          # Deprecated name of the option. Can be used for options that were renamed.
          # When `key` is missing from config and `legacy_key` is available, the value of
          # `legacy_key` is used, printing a deprecation warning in the logs.
          legacy_key: my_ext.legacy.flag.do_something

Dynamic config options
^^^^^^^^^^^^^^^^^^^^^^

There is a special option type, ``dynamic``. This option type is used for a set
of options that have common name-pattern. Because ``dynamic`` type defines
multiple options, it has no default, validators and serves mostly documentation
purposes. Let's use CKAN's ``sqlalchemy.*`` options as example. Every option
whose name follows the pattern ``sqlalchemy.SOMETHING`` is passed to the
SQLAlchemy engine created by CKAN. CKAN doesn't actually know which options
are valid and it's up to you to provide valid values. Basically, we have a set
of options with prefix ``sqlalchemy.``. If use these options without declararing,
it will trigger warnings about using undeclared options, which are harmless but can be
annoying. Declaring them helps to make explicit which configuration options are actually being used.
In order to declare such set of options, put some label surrounded with angle
brackets instead of the dynamic part of option's name. In our case it can be
``sqlalchemy.<OPTION>`` or ``sqlalchemy.<anything>``.  Any word can be used as
label, the only important part here are angle brackets::

  - key: sqlalchemy.<OPTION>
    type: dynamic
    description: |
      Example::

       sqlalchemy.pool_pre_ping=True
       sqlalchemy.pool_size=10
       sqlalchemy.max_overflow=20

      Custom sqlalchemy config parameters used to establish the main
      database connection.

Use this feature sparsely, only when you really want to declare literally ANY
value following the pattern. If you have finite set of possible options,
consider declaring all of them, because it allows you to provide validators,
defaults, and prevents you from accidental shadowing unrelated options.


Accessing config options
------------------------

Using validators ensures that config values are normalized. Up until now you have probably seen
code like this one::

  is_enabled = toolkit.asbool(toolkit.config.get("ckanext.my_ext.enable", False))

Declaring this configuration option and assigning validators (`convert_int`,
`boolean_validators`) and a default value means that we can use the
``config.get(key)`` instead of the expression above::

  is_enabled = toolkit.config.get("ckanext.my_ext.enable")

This will ensure that:

 1. If the value is not explicitly defined in the configuration file, the default one will be picked
 2. This value is passed to the validators, and a valid value is returned


.. note:: An attempt to use ``config.get()`` with an undeclared config option
          will print a warning to the logs and return the option value or ``None`` as default.


Command line interface
----------------------

The current configuration can be validated using the :ref:`config declaration CLI <cli.ckan.config>`::

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
        ckan.plugins = stats text_view datatables_view

   If the same option is set more than once in your config file, exeption will
   be raised and CKAN application will not start



.. include:: ../_config_options.inc
