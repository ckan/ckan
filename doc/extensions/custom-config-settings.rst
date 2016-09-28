==========================================
Using custom config settings in extensions
==========================================

Extensions can define their own custom config settings that users can add to
their CKAN config files to configure the behavior of the extension.

Continuing with the :py:class:`~ckan.plugins.interfaces.IAuthFunctions` example
from :doc:`tutorial`, let's make an alternative version of the extension that
allows users to create new groups if a new config setting
``ckan.iauthfunctions.users_can_create_groups`` is ``True``:

.. literalinclude:: ../../ckanext/example_iauthfunctions/plugin_v5_custom_config_setting.py

The ``group_create`` authorization function in this plugin uses
:py:obj:`config` to read the setting from the config file, then calls
:py:func:`ckan.plugins.toolkit.asbool` to convert the value from a string
(all config settings values are strings, when read from the file) to a boolean.

.. note::

   There are also :py:func:`~ckan.plugins.toolkit.asint` and
   :py:func:`~ckan.plugins.toolkit.aslist` functions in the plugins toolkit.

With this plugin enabled, you should find that users can create new groups if
you have ``ckan.iauthfunctions.users_can_create_groups = True`` in the
``[app:main]`` section of your CKAN config file. Otherwise, only sysadmin users
will be allowed to create groups.

.. note::

   Names of config settings provided by extensions should include the name
   of the extension, to avoid conflicting with core config settings or with
   config settings from other extensions.
   See :ref:`avoid name clashes`.

.. note::

   The users still need to be logged-in to create groups.
   In general creating, updating or deleting content in CKAN requires the user
   to be logged-in to a registered user account, no matter what the relevant
   authorization function says.
