=====================
Configuration Options
=====================

The functionality and features of CKAN can be modified using many different
configuration options. These are generally set in the `CKAN configuration file`_,
but some of them can also be set via `Environment variables`_ or at :ref:`runtime <runtime-config>`.



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

   If the same option is set more than once in your config file, the last
   setting given in the file will override the others.

General Settings
----------------

.. _debug:

debug
^^^^^

Example::

  debug = False

Default value: ``False``

This enables the `Flask-DebugToolbar
<https://flask-debugtoolbar.readthedocs.io/>`_ in the web interface, makes
Webassets serve unminified JS and CSS files, and enables CKAN templates'
debugging features.

You will need to ensure the ``Flask-DebugToolbar`` python package is installed,
by activating your ckan virtual environment and then running::

    pip install -r /usr/lib/ckan/default/src/ckan/dev-requirements.txt

If you are running CKAN on Apache, you must change the WSGI
configuration to run a single process of CKAN. Otherwise
the execution will fail with: ``AssertionError: The EvalException
middleware is not usable in a multi-process environment``. Eg. change::

  WSGIDaemonProcess ckan_default display-name=ckan_default processes=2 threads=15
  to
  WSGIDaemonProcess ckan_default display-name=ckan_default threads=15

.. warning:: This option should be set to ``False`` for a public site.
   With debug mode enabled, a visitor to your site could execute malicious
   commands.

ckan.legacy_route_mappings
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.legacy_route_mappings = {"home": "home.index", "about": "home.about",
                                  "search": "dataset.search"}

Default value: ``{"home": "home.index", "about": "home.about"}``

This can be used when using an extension that is still using old (Pylons-based) route names to
maintain compatibility.

  .. warning:: This configuration will be removed when migration to Flask is completed. Please
    update the extension code to use the new Flask-based route names.


Development Settings
--------------------

.. _ckan.devserver.threaded:

ckan.devserver.threaded
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.devserver.threaded = true

Default value: False

Controls, whether development server handle each request in a separate
thread.

.. _ckan.devserver.multiprocess:

ckan.devserver.multiprocess
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.devserver.multiprocess = 8

Default value: 1

If greater than 1 then handle each request in a new process up to this
maximum number of concurrent processes.

.. _ckan.devserver.watch_patterns:

ckan.devserver.watch_patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.devserver.watch_patterns = mytheme/**/*.yaml mytheme/**/*.json

Default value: None

A list of files the reloader should watch additionally to the
modules. For example configuration files.

Repoze.who Settings
-------------------

.. _who.timeout:

who.timeout
^^^^^^^^^^^

Example::

 who.timeout = 3600

Default value: None

This defines how long (in seconds) until a user is logged out after a period
of inactivity. If the setting isn't defined, the session doesn't expire. Not
active by default.

.. _who.httponly:

who.httponly
^^^^^^^^^^^^

Default value: True

This determines whether the HttpOnly flag will be set on the repoze.who
authorization cookie. The default in the absence of the setting is ``True``.
For enhanced security it is recommended to use the HttpOnly flag and not set
this to ``False``, unless you have a good reason for doing so.

.. _who.secure:

who.secure
^^^^^^^^^^

Example::

 who.secure = True

Default value: False

This determines whether the secure flag will be set for the repoze.who
authorization cookie. If ``True``, the cookie will be sent over HTTPS. The
default in the absence of the setting is ``False``.

.. _who.samesite:

who.samesite
^^^^^^^^^^^^

Example::

 who.samesite = Strict

Default value: Lax

This determines whether the SameSite flag will be set for the repoze.who
authorization cookie. Allowed values are ``Lax`` (the default one), ``Strict`` or ``None``.
If set to ``None``,  ``who.secure`` must be set to ``True``.


Database Settings
-----------------

.. _sqlalchemy.url:

sqlalchemy.url
^^^^^^^^^^^^^^

Example::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantest3

This defines the database that CKAN is to use. The format is::

 sqlalchemy.url = postgres://USERNAME:PASSWORD@HOST/DBNAME

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

Default value: ``english``

This can be ignored if you're not using the :doc:`datastore`.

The default language used when creating full-text search indexes and querying
them. It can be overwritten by the user by passing the "lang" parameter to
"datastore_search" and "datastore_create".

.. _ckan.datastore.default_fts_index_method:

ckan.datastore.default_fts_index_method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.default_fts_index_method = gist

Default value:  ``gist``

This can be ignored if you're not using the :doc:`datastore`.

The default method used when creating full-text search indexes. Currently it
can be "gin" or "gist". Refer to PostgreSQL's documentation to understand the
characteristics of each one and pick the best for your instance.

.. _ckan.datastore.sqlsearch.enabled:

ckan.datastore.sqlsearch.enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.sqlsearch.enabled = False

Default value:  ``True``

This option allows you to disable the datastore_search_sql action function, and
corresponding API endpoint if you do not wish it to be activated.

.. _ckan.datastore.search.rows_default:

ckan.datastore.search.rows_default
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.search.rows_default = 1000

Default value:  ``100``

Default number of rows returned by ``datastore_search``, unless the client
specifies a different ``limit`` (up to ``ckan.datastore.search.rows_max``).

NB this setting does not affect ``datastore_search_sql``.

.. _ckan.datastore.search.rows_max:

ckan.datastore.search.rows_max
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datastore.search.rows_max = 1000000

Default value:  ``32000``

Maximum allowed value for the number of rows returned by the datastore.

Specifically this limits:

* ``datastore_search``'s ``limit`` parameter.
* ``datastore_search_sql`` queries have this limit inserted.

Site Settings
-------------

.. _ckan.site_url:

ckan.site_url
^^^^^^^^^^^^^

Example::

  ckan.site_url = http://scotdata.ckan.net

Default value:  (an explicit value is mandatory)

Set this to the URL of your CKAN site. Many CKAN features that need an absolute URL to your
site use this setting.

This setting should only contain the protocol (e.g. ``http://``), host (e.g.
``www.example.com``) and (optionally) the port (e.g. ``:8080``). In particular,
if you have mounted CKAN at a path other than ``/`` then the mount point must
*not* be included in ``ckan.site_url``. Instead, you need to set
:ref:`ckan.root_path`.

.. important:: It is mandatory to complete this setting

.. warning::

  This setting should not have a trailing / on the end.


.. _apikey_header_name:

apikey_header_name
^^^^^^^^^^^^^^^^^^

Example::

 apikey_header_name = API-KEY

Default value: ``X-CKAN-API-Key`` & ``Authorization``

This allows another http header to be used to provide the CKAN API key. This is useful if network infrastructure blocks the Authorization header and ``X-CKAN-API-Key`` is not suitable.

.. _ckan.cache_expires:

ckan.cache_expires
^^^^^^^^^^^^^^^^^^

Example::

  ckan.cache_expires = 2592000

Default value: 0

This sets ``Cache-Control`` header's max-age value.

.. _ckan.cache_enabled:

ckan.cache_enabled
^^^^^^^^^^^^^^^^^^

Example::

  ckan.cache_enabled = True

Default value: ``False``

This enables cache control headers on all requests. If the user is not logged in and there is no session data a ``Cache-Control: public`` header will be added. For all other requests the ``Cache-control: private`` header will be added.

.. _ckan.use_pylons_response_cleanup_middleware:

ckan.use_pylons_response_cleanup_middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.use_pylons_response_cleanup_middleware = true

Default value: true

This enables middleware that clears the response string after it has been sent. This helps CKAN's memory management if CKAN repeatedly serves very large requests.

.. _ckan.mimetype_guess:

ckan.mimetype_guess
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.mimetype_guess = file_ext

Default value: ``file_ext``

There are three options for guessing the mimetype of uploaded or linked resources: file_ext, file_contents, None.

``file_ext`` will guess the mimetype by the url first, then the file extension.

``file_contents`` will guess the mimetype by the file itself, this tends to be inaccurate.

``None`` will not store the mimetype for the resource.

.. _ckan.static_max_age:

ckan.static_max_age
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.static_max_age = 2592000

Default value: ``3600``

Controls CKAN static files' cache max age, if we're serving and caching them.

.. _ckan.tracking_enabled:

ckan.tracking_enabled
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.tracking_enabled = True

Default value: ``False``

This controls if CKAN will track the site usage. For more info, read :ref:`tracking`.

ckan.valid_url_schemes
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.valid_url_schemes = http https ftp sftp

Default value: ``http https ftp``

Controls what uri schemes are rendered as links.

.. _config-authorization:

Authorization Settings
----------------------

More information about how authorization works in CKAN can be found the
:doc:`authorization` section.

.. start_config-authorization

.. _ckan.auth.anon_create_dataset:

ckan.auth.anon_create_dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.anon_create_dataset = False

Default value: ``False``

Allow users to create datasets without registering and logging in.


.. _ckan.auth.create_unowned_dataset:

ckan.auth.create_unowned_dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.create_unowned_dataset = False

Default value: ``True``


Allow the creation of datasets not owned by any organization.

.. _ckan.auth.create_dataset_if_not_in_organization:

ckan.auth.create_dataset_if_not_in_organization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.create_dataset_if_not_in_organization = False

Default value: ``True``


Allow users who are not members of any organization to create datasets,
default: true. ``create_unowned_dataset`` must also be True, otherwise
setting ``create_dataset_if_not_in_organization`` to True is meaningless.

.. _ckan.auth.user_create_groups:

ckan.auth.user_create_groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.user_create_groups = True

Default value: ``False``


Allow users to create groups.

.. _ckan.auth.user_create_organizations:

ckan.auth.user_create_organizations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.user_create_organizations = False

Default value: ``True``


Allow users to create organizations.

.. _ckan.auth.user_delete_groups:

ckan.auth.user_delete_groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.user_delete_groups = False

Default value: ``True``


Allow users to delete groups.

.. _ckan.auth.user_delete_organizations:

ckan.auth.user_delete_organizations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.user_delete_organizations = False

Default value: ``True``


Allow users to delete organizations.

.. _ckan.auth.create_user_via_api:

ckan.auth.create_user_via_api
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.create_user_via_api = False

Default value: ``False``


Allow new user accounts to be created via the API by anyone. When ``False`` only sysadmins are authorised.

.. _ckan.auth.create_user_via_web:

ckan.auth.create_user_via_web
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.create_user_via_web = True

Default value: ``True``


Allow new user accounts to be created via the Web.

.. _ckan.auth.roles_that_cascade_to_sub_groups:

ckan.auth.roles_that_cascade_to_sub_groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.auth.roles_that_cascade_to_sub_groups = admin editor

Default value: ``admin``


Makes role permissions apply to all the groups or organizations down the hierarchy from the groups or organizations that the role is applied to.

e.g. a particular user has the 'admin' role for group 'Department of Health'. If you set the value of this option to 'admin' then the user will automatically have the same admin permissions for the child groups of 'Department of Health' such as 'Cancer Research' (and its children too and so on).


.. _ckan.auth.public_user_details:

ckan.auth.public_user_details
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.public_user_details = False

Default value: ``True``

Restricts anonymous access to user information. If is set to ``False`` accessing users details when not logged in will raise a ``Not Authorized`` exception.

.. note:: This setting should be used when user registration is disabled (``ckan.auth.create_user_via_web = False``), otherwise users
    can just create an account to see other users details.


.. _ckan.auth.public_activity_stream_detail:

ckan.auth.public_activity_stream_detail
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.public_activity_stream_detail = True

Default value: ``False`` (however the default config file template sets it to ``True``)

Restricts access to 'view this version' and 'changes' in the Activity Stream pages. These links provide users with the full edit history of datasets etc - what they showed in the past and the diffs between versions. If this option is set to ``False`` then only admins (e.g. whoever can edit the dataset) can see this detail. If set to ``True``, anyone can see this detail (assuming they have permission to view the dataset etc).


.. _ckan.auth.allow_dataset_collaborators:

ckan.auth.allow_dataset_collaborators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.allow_dataset_collaborators = True

Default value: ``False``

Enables or disable collaborators in individual datasets. If ``True``, in addition to the standard organization based permissions, users can be added as collaborators to individual datasets with different roles, regardless of the organization they belong to. For more information, check the documentation on :ref:`dataset_collaborators`.

.. warning:: If this setting is turned off in a site where there already were collaborators created, you must reindex all datasets to update the permission labels, in order to prevent access to private datasets to the previous collaborators.

.. _ckan.auth.allow_admin_collaborators:

ckan.auth.allow_admin_collaborators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.allow_admin_collaborators = True

Default value: ``False``


Allows dataset collaborators to have the "Admin" role, allowing them to add more collaborators or remove existing ones. By default collaborators can only be managed by administrators of the organization the dataset belongs to. For more information, check the documentation on :ref:`dataset_collaborators`.


.. warning:: If this setting is turned off in a site where admin collaborators have been already created, existing collaborators with role "admin" will no longer be able to add or remove collaborators, but they will still be able to edit and access the datasets that they are assinged to.

.. _ckan.auth.allow_collaborators_to_change_owner_org:

ckan.auth.allow_collaborators_to_change_owner_org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.allow_collaborators_to_change_owner_org = True

Default value: ``False``


Allows dataset collaborators to change the owner organization of the datasets they are collaborators on. Defaults to False, meaning that collaborators with role admin or editor can edit the dataset metadata but not the organization field.

.. _ckan.auth.create_default_api_keys:

ckan.auth.create_default_api_keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.auth.create_default_api_keys = True

Default value: ``False``


Determines if a an API key should be automatically created for every user when creating a user account. If set to False (the default value), users can manually create an API token from their profile instead. See :ref:`api authentication`: for more details.


.. end_config-authorization

.. _config-api-tokens:

API Token Settings
------------------

.. _api_token.nbytes:

api_token.nbytes
^^^^^^^^^^^^^^^^

Example::

  api_token.nbytes = 20

Default value: 32

Number of bytes used to generate unique id for API Token.

.. _api_token.jwt.encode.secret:

api_token.jwt.encode.secret
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  api_token.jwt.encode.secret = file:/path/to/private/key

Default value: same as ``beaker.session.secret`` config option with ``string:`` type.

A key suitable for the chosen algorithm(``api_token.jwt.algorithm``):

* for asymmetric algorithms: path to private key with ``file:`` prefix. I.e ``file:/path/private/key``
* for symmetric algorithms: plain string, sufficiently long for security with ``string:`` prefix. I.e ``string:123abc``

Value must have prefix, which defines its type. Supported prefixes are:

* ``string:`` - Plain string, will be used as is.
* ``file:`` - Path to file. Content of the file will be used as key.

.. _api_token.jwt.decode.secret:

api_token.jwt.decode.secret
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  api_token.jwt.decode.secret = file:/path/to/public/key.pub

Default value: same as ``beaker.session.secret`` config option with ``string:`` type.

A key suitable for the chosen algorithm(``api_token.jwt.algorithm``):

* for asymmetric algorithms: path to public key with ``file:`` prefix. I.e ``file:/path/public/key.pub``
* for symmetric algorithms: plain string, sufficiently long for security with ``string:`` prefix. I.e ``string:123abc``

Value must have prefix, which defines it's type. Supported prefixes are:

* ``string:`` - Plain string, will be used as is.
* ``file:`` - Path to file. Content of the file will be used as key.

.. _api_token.jwt.algorithm:

api_token.jwt.algorithm
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  api_token.jwt.algorithm = RS256

Default value: ``HS256``

Algorithm to sign the token with, e.g. "ES256", "RS256"

Search Settings
---------------

.. _ckan.site_id:

ckan.site_id
^^^^^^^^^^^^

Example::

 ckan.site_id = my_ckan_instance

CKAN uses Solr to index and search packages. The search index is linked to the value of the ``ckan.site_id``, so if you have more than one
CKAN instance using the same `solr_url`_, they will each have a separate search index as long as their ``ckan.site_id`` values are different. If you are only running
a single CKAN instance then this can be ignored.

Note, if you change this value, you need to rebuild the search index.

.. _solr_url:

solr_url
^^^^^^^^

Example::

 solr_url = http://solr.okfn.org:8983/solr/ckan-schema-2.0

Default value:  ``http://127.0.0.1:8983/solr``

This configures the Solr server used for search. The Solr schema found at that URL must be one of the ones in ``ckan/config/solr`` (generally the most recent one). A check of the schema version number occurs when CKAN starts.

Optionally, ``solr_user`` and ``solr_password`` can also be configured to specify HTTP Basic authentication details for all Solr requests.

.. note::  If you change this value, you need to rebuild the search index.

.. _ckan.search.automatic_indexing:

ckan.search.automatic_indexing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.automatic_indexing = true

Default value: ``true``

Make all changes immediately available via the search after editing or
creating a dataset. Default is true. If for some reason you need the indexing
to occur asynchronously, set this option to false.

.. note:: This is equivalent to explicitly load the ``synchronous_search`` plugin.

.. _ckan.search.solr_commit:

ckan.search.solr_commit
^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.solr_commit = false

Default value:  ``true``

Make ckan commit changes solr after every dataset update change. Turn this to false if on solr 4.0 and you have automatic (soft)commits enabled to improve dataset update/create speed (however there may be a slight delay before dataset gets seen in results).

.. _ckan.search.show_all_types:

ckan.search.show_all_types
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.show_all_types = dataset

Default value:  ``false``

Controls whether a search page (e.g. ``/dataset``) should also show
custom dataset types. The default is ``false`` meaning that no search
page for any type will show other types. ``true`` will show other types
on the ``/dataset`` search page. Any other value (e.g. ``dataset`` or
``document`` will be treated as a dataset type and that type's search
page will show datasets of all types.

.. _ckan.search.default_include_private:

ckan.search.default_include_private
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.default_include_private = false

Default value:  ``true``

Controls whether the default search page (``/dataset``) should include
private datasets visible to the current user or only public datasets
visible to everyone.

.. _ckan.search.default_package_sort:

ckan.search.default_package_sort
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.default_package_sort = "name asc"

Default value:  ``score desc, metadata_modified desc``

Controls whether the default search page (``/dataset``) should different
sorting parameter by default when the request does not specify sort.


.. _search.facets.limit:

search.facets.limit
^^^^^^^^^^^^^^^^^^^

Example::

 search.facets.limit = 100

Default value:  ``50``

Sets the default number of searched facets returned in a query.

.. _search.facets.default:

search.facets.default
^^^^^^^^^^^^^^^^^^^^^

Example::

  search.facets.default = 10

Default number of facets shown in search results.  Default 10.

.. _ckan.extra_resource_fields:

ckan.extra_resource_fields
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.extra_resource_fields = alt_url

Default value: ``None``

List of the extra resource fields that would be used when searching.

.. _ckan.search.rows_max:

ckan.search.rows_max
^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.search.rows_max = 1000

Default value:  ``1000``

Maximum allowed value for rows returned. Specifically this limits:

* ``package_search``'s ``rows`` parameter
* ``group_show`` and ``organization_show``'s number of datasets returned when specifying ``include_datasets=true``

.. _ckan.group_and_organization_list_max:

ckan.group_and_organization_list_max
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.group_and_organization_list_max = 1000

Default value: ``1000``

Maximum number of groups/organizations returned when listing them. Specifically this limits:

* ``group_list``'s ``limit`` when ``all_fields=false``
* ``organization_list``'s ``limit`` when ``all_fields=false``

.. _ckan.group_and_organization_list_all_fields_max:

ckan.group_and_organization_list_all_fields_max
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.group_and_organization_list_all_fields_max = 100

Default value: ``25``

Maximum number of groups/organizations returned when listing them in detail. Specifically this limits:

* ``group_list``'s ``limit`` when ``all_fields=true``
* ``organization_list``'s ``limit`` when ``all_fields=true``

Redis Settings
---------------

.. _ckan_redis_url:

ckan.redis.url
^^^^^^^^^^^^^^

Example::

    ckan.redis.url = redis://localhost:7000/1

Default value: ``redis://localhost:6379/0``

URL to your Redis instance, including the database to be used.

.. versionadded:: 2.7


CORS Settings
-------------

Cross-Origin Resource Sharing (CORS) can be enabled and controlled with the following settings:

.. _ckan.cors.origin_allow_all:

ckan.cors.origin_allow_all
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.cors.origin_allow_all = True

This setting must be present to enable CORS. If True, all origins will be allowed (the response header Access-Control-Allow-Origin is set to '*'). If False, only origins from the ``ckan.cors.origin_whitelist`` setting will be allowed.

.. _ckan.cors.origin_whitelist:

ckan.cors.origin_whitelist
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.cors.origin_whitelist = http://www.myremotedomain1.com http://myremotedomain1.com

A space separated list of allowable origins. This setting is used when ``ckan.cors.origin_allow_all = False``.


Plugins Settings
----------------

.. _ckan.plugins:

ckan.plugins
^^^^^^^^^^^^

Example::

  ckan.plugins = disqus datapreview googleanalytics follower

Default value: ``stats text_view recline_view``

Specify which CKAN plugins are to be enabled.

.. warning::  If you specify a plugin but have not installed the code,  CKAN will not start.

Format as a space-separated list of the plugin names. The plugin name is the key in the ``[ckan.plugins]`` section of the extension's ``setup.py``. For more information on plugins and extensions, see :doc:`/extensions/index`.

.. note::

    The order of the plugin names in the configuration file influences the
    order that CKAN will load the plugins in. As long as each plugin class is
    implemented in a separate Python module (i.e. in a separate Python source
    code file), the plugins will be loaded in the order given in the
    configuration file.

    When multiple plugins are implemented in the same Python module, CKAN will
    process the plugins in the order that they're given in the config file, but as
    soon as it reaches one plugin from a given Python module, CKAN will load all
    plugins from that Python module, in the order that the plugin classes are
    defined in the module.

    For simplicity, we recommend implementing each plugin class in its own Python
    module.

    Plugin loading order can be important, for example for plugins that add custom
    template files: templates found in template directories added earlier will
    override templates in template directories added later.

    .. todo::

        Fix CKAN's plugin loading order to simply load all plugins in the order
        they're given in the config file, regardless of which Python modules
        they're implemented in.

.. _ckanext.stats.cache_enabled:

ckanext.stats.cache_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckanext.stats.cache_enabled = True

Default value:  ``True``

This controls if we'll use the 1 day cache for stats.


.. _ckan.resource_proxy.max_file_size:

ckan.resource_proxy.max_file_size
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.resource_proxy.max_file_size = 1048576

Default value:  ``1048576`` (1 MB)

This sets the upper file size limit for in-line previews.
Increasing the value allows CKAN to preview larger files (e.g. PDFs) in-line;
however, a higher value might cause time-outs, or unresponsive browsers for CKAN users
with lower bandwidth. If left commented out, CKAN will default to 1 MB.


.. _ckan.resource_proxy.chunk_size:

ckan.resource_proxy.chunk_size
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.resource_proxy.chunk_size = 8192

Default value:  ``4096``

This sets size of the chunk to read and write when proxying.
Raising this value might save some CPU cycles. It makes no sense to lower it
below the page size, which is default.


Front-End Settings
------------------

.. start_config-front-end

.. _ckan.site_title:

ckan.site_title
^^^^^^^^^^^^^^^

Example::

 ckan.site_title = Open Data Scotland

Default value:  ``CKAN``

This sets the name of the site, as displayed in the CKAN web interface.

.. _ckan.site_description:

ckan.site_description
^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.site_description = The easy way to get, use and share data

Default value:  (none)

This is for a description, or tag line for the site, as displayed in the header of the CKAN web interface.

.. _ckan.site_intro_text:

ckan.site_intro_text
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.site_intro_text = Nice introductory paragraph about CKAN or the site in general.

Default value:  (none)

This is for an introductory text used in the default template's index page.

.. _ckan.site_logo:

ckan.site_logo
^^^^^^^^^^^^^^

Example::

 ckan.site_logo = /images/ckan_logo_fullname_long.png

Default value:  (none)

This sets the logo used in the title bar.

.. _ckan.site_about:

ckan.site_about
^^^^^^^^^^^^^^^

Example::

 ckan.site_about = A _community-driven_ catalogue of _open data_ for the Greenfield area.

Default value::

  <p>CKAN is the world’s leading open-source data portal platform.</p>

  <p>CKAN is a complete out-of-the-box software solution that makes data
  accessible and usable – by providing tools to streamline publishing, sharing,
  finding and using data (including storage of data and provision of robust data
  APIs). CKAN is aimed at data publishers (national and regional governments,
  companies and organizations) wanting to make their data open and available.</p>

  <p>CKAN is used by governments and user groups worldwide and powers a variety
  of official and community data portals including portals for local, national
  and international government, such as the UK’s <a href="http://data.gov.uk">data.gov.uk</a>
  and the European Union’s <a href="http://publicdata.eu/">publicdata.eu</a>,
  the Brazilian <a href="http://dados.gov.br/">dados.gov.br</a>, Dutch and
  Netherland government portals, as well as city and municipal sites in the US,
  UK, Argentina, Finland and elsewhere.</p>

  <p>CKAN: <a href="http://ckan.org/">http://ckan.org/</a><br />
  CKAN Tour: <a href="http://ckan.org/tour/">http://ckan.org/tour/</a><br />
  Features overview: <a href="http://ckan.org/features/">http://ckan.org/features/</a></p>

Format tips:

* multiline strings can be used by indenting following lines

* the format is Markdown

.. note:: Whilst the default text is translated into many languages (switchable in the page footer), the text in this configuration option will not be translatable.
          For this reason, it's better to overload the snippet in ``home/snippets/about_text.html``. For more information, see :doc:`/theming/index`.

.. _ckan.main_css:

ckan.main_css
^^^^^^^^^^^^^

Example::

  ckan.main_css = /base/css/my-custom.css

Default value: ``/base/css/main.css``

With this option, instead of using the default `main.css`, you can use your own.

.. _ckan.favicon:

ckan.favicon
^^^^^^^^^^^^

Example::

 ckan.favicon = http://okfn.org/wp-content/themes/okfn-master-wordpress-theme/images/favicon.ico

Default value: ``/images/icons/ckan.ico``

This sets the site's `favicon`. This icon is usually displayed by the browser in the tab heading and bookmark.

.. _ckan.legacy_templates:

ckan.legacy_templates
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.legacy_templates = True

Default value: ``False``

This controls if the legacy genshi templates are used.

.. note:: This is option is **deprecated** and has no effect any more.

.. _ckan.datasets_per_page:

ckan.datasets_per_page
^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datasets_per_page = 10

Default value:  ``20``

This controls the pagination of the dataset search results page. This is the maximum number of datasets viewed per page of results.

.. _package_hide_extras:

package_hide_extras
^^^^^^^^^^^^^^^^^^^

Example::

 package_hide_extras = my_private_field other_field

Default value:  (empty)

This sets a space-separated list of extra field key values which will not be shown on the dataset read page.

.. warning::  While this is useful to e.g. create internal notes, it is not a security measure. The keys will still be available via the API and in revision diffs.

.. _ckan.dumps_url:

ckan.dumps_url
^^^^^^^^^^^^^^

If there is a page which allows you to download a dump of the entire catalogue
then specify the URL here, so that it can be advertised in the
web interface. For example::

  ckan.dumps_url = http://ckan.net/dump/

For more information on using dumpfiles, see :ref:`datasets dump`.

.. _ckan.dumps_format:

ckan.dumps_format
^^^^^^^^^^^^^^^^^

If there is a page which allows you to download a dump of the entire catalogue
then specify the format here, so that it can be advertised in the
web interface. ``dumps_format`` is just a string for display. Example::

  ckan.dumps_format = CSV/JSON

.. _ckan.recaptcha.publickey:

ckan.recaptcha.publickey
^^^^^^^^^^^^^^^^^^^^^^^^

The public key for your reCAPTCHA account, for example::

 ckan.recaptcha.publickey = 6Lc...-KLc

To get a reCAPTCHA account, sign up at: http://www.google.com/recaptcha

.. _ckan.recaptcha.privatekey:

ckan.recaptcha.privatekey
^^^^^^^^^^^^^^^^^^^^^^^^^

The private key for your reCAPTCHA account, for example::

 ckan.recaptcha.privatekey = 6Lc...-jP

Setting both :ref:`ckan.recaptcha.publickey` and
:ref:`ckan.recaptcha.privatekey` adds captcha to the user registration form.
This has been effective at preventing bots registering users and creating spam
packages.

.. _ckan.featured_groups:

ckan.featured_groups
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.featured_groups = group_one

Default Value: (empty)

Defines a list of group names or group ids. This setting is used to display a
group and datasets on the home page in the default templates (1 group and 2
datasets are displayed).

.. _ckan.featured_organizations:

ckan.featured_orgs
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.featured_orgs = org_one

Default Value: (empty)

Defines a list of organization names or ids. This setting is used to display
an organization and datasets on the home page in the default templates (1
group and 2 datasets are displayed).

.. _ckan.default_group_sort:

ckan.default_group_sort
^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.default_group_sort = name

Default Value: 'title'

Defines if some other sorting is used in group_list and organization_list
by default when the request does not specify sort.

.. _ckan.gravatar_default:

ckan.gravatar_default
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.gravatar_default = disabled

Default value: ``identicon``

This controls the default gravatar style. Gravatar is used by default when a user has not set a custom profile picture,
but it can be turn completely off by setting this option to "disabled". In that case, a placeholder image will be shown
instead, which can be customized overriding the ``templates/user/snippets/placeholder.html`` template.

.. _ckan.debug_supress_header:

ckan.debug_supress_header
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.debug_supress_header = False

Default value: ``False``

This configs if the debug information showing the controller and action
receiving the request being is shown in the header.

.. note:: This info only shows if debug is set to True.

.. end_config-front-end

Resource Views Settings
-----------------------

.. start_resource-views

.. _ckan.views.default_views:

ckan.views.default_views
^^^^^^^^^^^^^^^^^^^^^^^^

Example::


 ckan.views.default_views = image_view webpage_view recline_grid_view

Default value: ``image_view recline_view``

Defines the resource views that should be created by default when creating or
updating a dataset. From this list only the views that are relevant to a particular
resource format will be created. This is determined by each individual view.

If not present (or commented), the default value is used. If left empty, no
default views are created.

.. note:: You must have the relevant view plugins loaded on the ``ckan.plugins``
    setting to be able to create the default views, eg::

        ckan.plugins = image_view webpage_view recline_grid_view ...

        ckan.views.default_views = image_view webpage_view recline_grid_view

.. _ckan.preview.json_formats:

ckan.preview.json_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.json_formats = json

Default value: ``json``

Space-delimited list of JSON based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.xml_formats:

ckan.preview.xml_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.xml_formats = xml rdf rss

Default value: ``xml rdf rdf+xml owl+xml atom rss``

Space-delimited list of XML based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.text_formats:

ckan.preview.text_formats
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.text_formats = text plain

Default value: ``text plain text/plain``

Space-delimited list of plain text based resource formats that will be rendered by the Text view plugin (``text_view``)

.. _ckan.preview.image_formats:

ckan.preview.image_formats
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.image_formats = png jpeg jpg gif

Default value: ``png jpeg jpg gif``

Space-delimited list of image-based resource formats that will be rendered by the Image view plugin (``image_view``)


.. _ckan.recline.dataproxy_url:

ckan.recline.dataproxy_url
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.recline.dataproxy_url = https://mydataproxy.example.com

Default value: ``//jsonpdataproxy.appspot.com``

Custom URL to a self-hosted DataProxy instance. The DataProxy is an external service currently used to stream data in
JSON format to the Recline-based views when data is not on the DataStore. The main instance is deprecated and will
be eventually shut down, so users that require it can host an instance themselves and use this configuration option
to point Recline to it.

.. end_resource-views

Theming Settings
----------------

.. start_config-theming

.. _ckan.template_head_end:

ckan.template_head_end
^^^^^^^^^^^^^^^^^^^^^^

HTML content to be inserted just before ``</head>`` tag (e.g. extra stylesheet)

Example::

  ckan.template_head_end = <link rel="stylesheet" href="http://mysite.org/css/custom.css" type="text/css">

You can also have multiline strings. Just indent following lines. e.g.::

 ckan.template_head_end =
  <link rel="stylesheet" href="/css/extra1.css" type="text/css">
  <link rel="stylesheet" href="/css/extra2.css" type="text/css">

.. note:: This is only for legacy code, and shouldn't be used anymore.

.. _ckan.template_footer_end:

ckan.template_footer_end
^^^^^^^^^^^^^^^^^^^^^^^^

HTML content to be inserted just before ``</body>`` tag (e.g. Google Analytics code).

.. note:: you can have multiline strings (just indent following lines)

Example (showing insertion of Google Analytics code)::

  ckan.template_footer_end = <!-- Google Analytics -->
    <script src='http://www.google-analytics.com/ga.js' type='text/javascript'></script>
    <script type="text/javascript">
    try {
    var pageTracker = _gat._getTracker("XXXXXXXXX");
    pageTracker._setDomainName(".ckan.net");
    pageTracker._trackPageview();
    } catch(err) {}
    </script>
    <!-- /Google Analytics -->

.. note:: This is only for legacy code, and shouldn't be used anymore.

.. _ckan.template_title_delimiter:

ckan.template_title_delimiter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.template_title_delimiter = |

Default value:  ``-``

This sets the delimiter between the site's subtitle (if there's one) and its title, in HTML's ``<title>``.

.. _extra_template_paths:

extra_template_paths
^^^^^^^^^^^^^^^^^^^^

Example::

 extra_template_paths = /home/okfn/brazil_ckan_config/templates

Use this option to specify where CKAN should look for additional templates, before reverting to the ``ckan/templates`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`/theming/index`.

.. _extra_public_paths:

extra_public_paths
^^^^^^^^^^^^^^^^^^

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for static files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for additional files, before reverting to the ``ckan/public`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`/theming/index`.

.. _ckan.base_public_folder:

ckan.base_public_folder
^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.base_public_folder = public

Default value:  ``public``

This config option is used to configure the base folder for static files used
by CKAN core. It is currently unused and it only accepts one value: ``public``
(Bootstrap 3, the default value from CKAN 2.8 onwards).

.. _ckan.base_templates_folder:

ckan.base_templates_folder
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.base_templates_folder = templates

Default value:  ``templates``

This config option is used to configure the base folder for templates used
by CKAN core. It is currently unused and it only accepts one vaue: ``templates``
(Bootstrap 3, the default value from CKAN 2.8 onwards).

.. end_config-theming

Storage Settings
----------------

.. _ckan.storage_path:

ckan.storage_path
^^^^^^^^^^^^^^^^^

Example::
    ckan.storage_path = /var/lib/ckan

Default value:  ``None``

This defines the location of where CKAN will store all uploaded data.

.. _ckan.max_resource_size:

ckan.max_resource_size
^^^^^^^^^^^^^^^^^^^^^^

Example::
    ckan.max_resource_size = 100

Default value: ``10``

The maximum in megabytes a resources upload can be.

.. _ckan.max_image_size:

ckan.max_image_size
^^^^^^^^^^^^^^^^^^^^

Example::
    ckan.max_image_size = 10

Default value: ``2``

The maximum in megabytes an image upload can be.


Webassets Settings
------------------

.. _ckan.webassets.path:

ckan.webassets.path
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.webassets.path = /var/lib/ckan/webassets

Default value: ``webassets`` folder under the path specified by the
:ref:`ckan.storage_path` option.

In order to increase performance, static assets (CSS and JS files) included via an ``asset`` tag inside templates are compiled only once,
when the asset is used for the first time. All subsequent requests to the
asset will use the existing file. CKAN stores the compiled webassets in the file system, in the path specified by this config option.


.. _ckan.webassets.use_x_sendfile:

ckan.webassets.use_x_sendfile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.webassets.use_x_sendfile = true

Default value: ``false``

When serving static files, if this setting is ``True``, the applicatin will set the ``X-Sendfile`` header instead of
serving the files directly with Flask. This will increase performance when serving the assets, but it
requires that the web server (eg Nginx) supports the ``X-Sendfile`` header. See :ref:`x-sendfile` for more information.


DataPusher Settings
-------------------

.. _ckan.datapusher.formats:

ckan.datapusher.formats
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.formats = csv xls

Default value: ``csv xls xlsx tsv application/csv application/vnd.ms-excel application/vnd.openxmlformats-officedocument.spreadsheetml.sheet``

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

Default value:  ``3600`` (one hour)

In case a DataPusher task gets stuck and fails to recover, this is the minimum
amount of time (in seconds) after a resource is submitted to DataPusher that the
resource can be submitted again.


User Settings
-------------------------

.. _ckan.user_list_limit:

ckan.user_list_limit
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.user_list_limit = 50

Default value: ``20``

This controls the number of users to show in the Users list. By default, it shows 20 users.


Activity Streams Settings
-------------------------

.. _ckan.activity_streams_enabled:

ckan.activity_streams_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.activity_streams_enabled = False

Default value:  ``True``

Turns on and off the activity streams used to track changes on datasets, groups, users, etc

.. _ckan.activity_streams_email_notifications:

ckan.activity_streams_email_notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.activity_streams_email_notifications = False

Default value:  ``False``

Turns on and off the activity streams' email notifications. You'd also need to setup a cron job to send
the emails. For more information, visit :ref:`email-notifications`.

.. _ckan.activity_list_limit:

ckan.activity_list_limit
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.activity_list_limit = 31

Default value: ``31``

This controls the number of activities to show in the Activity Stream.

.. _ckan.activity_list_limit_max:

ckan.activity_list_limit_max
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.activity_list_limit_max = 100

Default value: ``100``

Maximum allowed value for Activity Stream ``limit`` parameter.

.. _ckan.email_notifications_since:

ckan.email_notifications_since
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.email_notifications_since = 2 days

Default value: ``infinite``

Email notifications for events older than this time delta will not be sent.
Accepted formats: '2 days', '14 days', '4:35:00' (hours, minutes, seconds), '7 days, 3:23:34', etc.

.. _ckan.hide_activity_from_users:

ckan.hide_activity_from_users
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

    ckan.hide_activity_from_users = sysadmin

Hides activity from the specified users from activity stream. If unspecified,
it'll use :ref:`ckan.site_id` to hide activity by the site user. The site user
is a sysadmin user on every ckan user with a username that's equal to
:ref:`ckan.site_id`. This user is used by ckan for performing actions from the
command-line.

.. _config-feeds:

Feeds Settings
--------------

.. _ckan.feeds.author_name:

ckan.feeds.author_name
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.author_name = Michael Jackson

Default value: ``(none)``

This controls the feed author's name. If unspecified, it'll use :ref:`ckan.site_id`.

.. _ckan.feeds.author_link:

ckan.feeds.author_link
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.author_link = http://okfn.org

Default value: ``(none)``

This controls the feed author's link. If unspecified, it'll use :ref:`ckan.site_url`.

.. _ckan.feeds.authority_name:

ckan.feeds.authority_name
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.authority_name = http://okfn.org

Default value: ``(none)``

The domain name or email address of the default publisher of the feeds and elements. If unspecified, it'll use :ref:`ckan.site_url`.

.. _ckan.feeds.date:

ckan.feeds.date
^^^^^^^^^^^^^^^

Example::

  ckan.feeds.date = 2012-03-22

Default value: ``(none)``

A string representing the default date on which the authority_name is owned by the publisher of the feed.


.. _config-i18n:

Internationalisation Settings
-----------------------------

.. _ckan.locale_default:

ckan.locale_default
^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_default = de

Default value:  ``en`` (English)

Use this to specify the locale (language of the text) displayed in the CKAN Web UI. This requires a suitable `mo` file installed for the locale in the ckan/i18n. For more information on internationalization, see :doc:`/contributing/i18n`. If you don't specify a default locale, then it will default to the first locale offered, which is by default English (alter that with `ckan.locales_offered` and `ckan.locales_filtered_out`.

.. note: In versions of CKAN before 1.5, the settings used for this was variously `lang` or `ckan.locale`, which have now been deprecated in favour of `ckan.locale_default`.

.. _ckan.locales_offered:

ckan.locales_offered
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_offered = en de fr

Default value: (none)

By default, all locales found in the ``ckan/i18n`` directory will be offered to the user. To only offer a subset of these, list them under this option. The ordering of the locales is preserved when offered to the user.

.. _ckan.locales_filtered_out:

ckan.locales_filtered_out
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_filtered_out = pl ru

Default value: (none)

If you want to not offer particular locales to the user, then list them here to have them removed from the options.

.. _ckan.locale_order:

ckan.locale_order
^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_order = fr de

Default value: (none)

If you want to specify the ordering of all or some of the locales as they are offered to the user, then specify them here in the required order. Any locales that are available but not specified in this option, will still be offered at the end of the list.

.. _ckan.i18n_directory:

ckan.i18n_directory
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n_directory = /opt/locales/i18n/

Default value: (none)

By default, the locales are searched for in the ``ckan/i18n`` directory. Use this option if you want to use another folder.

.. _ckan.i18n.extra_directory:

ckan.i18n.extra_directory
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n.extra_directory = /opt/ckan/extra_translations/

Default value: (none)

If you wish to add extra translation strings and have them merged with the
default ckan translations at runtime you can specify the location of the extra
translations using this option.

.. _ckan.i18n.extra_gettext_domain:

ckan.i18n.extra_gettext_domain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n.extra_gettext_domain = mydomain

Default value: (none)

You can specify the name of the gettext domain of the extra translations. For
example if your translations are stored as
``i18n/<locale>/LC_MESSAGES/somedomain.mo`` you would want to set this option
to ``somedomain``

.. _ckan.i18n.extra_locales:

ckan.i18n.extra_locales
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n.extra_locales = fr es de

Default value: (none)

If you have set an extra i18n directory using ``ckan.i18n.extra_directory``, you
should specify the locales that have been translated in that directory in this
option.

.. _ckan.i18n.rtl_languages:

ckan.i18n.rtl_languages
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n.rtl_languages = he ar fa_IR

Default value: ``he ar fa_IR``

Allows to modify the right-to-left languages

.. _ckan.i18n.rtl_css:

ckan.i18n.rtl_css
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n.rtl_css = /base/css/my-custom-rtl.css

Default value: ``/base/css/rtl.css``

Allows to override the default rtl css file used for the languages defined
in ``ckan.i18n.rtl_languages``.

.. _ckan.display_timezone:

ckan.display_timezone
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.display_timezone = Europe/Zurich

Default value: UTC

By default, all datetimes are considered to be in the UTC timezone. Use this option to change the displayed dates on the frontend. Internally, the dates are always saved as UTC. This option only changes the way the dates are displayed.

The valid values for this options [can be found at pytz](http://pytz.sourceforge.net/#helpers) (``pytz.all_timezones``). You can specify the special value `server` to use the timezone settings of the server, that is running CKAN.

.. _ckan.root_path:

ckan.root_path
^^^^^^^^^^^^^^

Example::

  ckan.root_path = /my/custom/path/{{LANG}}/foo

Default value: (none)

This setting is used to construct URLs inside CKAN. It specifies two things:

* *At which path CKAN is mounted:* By default it is assumed that CKAN is mounted
  at ``/``, i.e. at the root of your web server. If you have configured your
  web server to serve CKAN from a different mount point then you need to
  duplicate that setting here.

* *Where the locale is added to an URL:* By default, URLs are formatted as
  ``/some/url`` when using the default locale, or ``/de/some/url`` when using
  the ``de`` locale, for example. When ``ckan.root_path`` is set it must
  include the string ``{{LANG}}``, which will be replaced by the locale.

.. important::

    The setting must contain ``{{LANG}}`` exactly as written here. Do not add
    spaces between the brackets.

.. seealso::

    The host of your CKAN installation can be set via :ref:`ckan.site_url`.

The CKAN repoze config file ``who.ini`` file will also need to be edited
by adding the path prefix to the options in the ``[plugin:friendlyform]``
section: ``login_form_url``, ``post_login_url`` and ``post_logout_url``.
Do not change the login/logout_handler_path options.

.. _ckan.resource_formats:

ckan.resource_formats
^^^^^^^^^^^^^^^^^^^^^

Example::
    ckan.resource_formats = /path/to/resource_formats

Default value: ckan/config/resource_formats.json

The purpose of this file is to supply a thorough list of resource formats
and to make sure the formats are normalized when saved to the database
and presented.

The format of the file is a JSON object with following format::

    ["Format", "Description", "Mimetype", ["List of alternative representations"]]

Please look in ckan/config/resource_formats.json for full details and and as an
example.


Form Settings
-------------

.. ckan.dataset.create_on_ui_requires_resources

ckan.dataset.create_on_ui_requires_resources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::
    ckan.dataset.create_on_ui_requires_resources = False

Default value: True

If False, there is no need to add any resources when creating a new dataset.


.. _package_new_return_url:

package_new_return_url
^^^^^^^^^^^^^^^^^^^^^^

The URL to redirect the user to after they've submitted a new package form,
example::

 package_new_return_url = http://datadotgc.ca/new_dataset_complete?name=<NAME>

This is useful for integrating CKAN's new dataset form into a third-party
interface, see :doc:`form-integration`.

The ``<NAME>`` string is replaced with the name of the dataset created.

.. _package_edit_return_url:

package_edit_return_url
^^^^^^^^^^^^^^^^^^^^^^^

The URL to redirect the user to after they've submitted an edit package form,
example::

 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

This is useful for integrating CKAN's edit dataset form into a third-party
interface, see :doc:`form-integration`.

The ``<NAME>`` string is replaced with the name of the dataset that was edited.

.. _licenses_group_url:

licenses_group_url
^^^^^^^^^^^^^^^^^^

A url pointing to a JSON file containing a list of license objects. This list
determines the licenses offered by the system to users, for example when
creating or editing a dataset.

This is entirely optional - by default, the system will use an internal cached
version of the CKAN list of licenses available from the
http://licenses.opendefinition.org/licenses/groups/ckan.json.

More details about the license objects - including the license format and some
example license lists - can be found at the `Open Licenses Service
<http://licenses.opendefinition.org/>`_.

Examples::

 licenses_group_url = file:///path/to/my/local/json-list-of-licenses.json
 licenses_group_url = http://licenses.opendefinition.org/licenses/groups/od.json

.. _email-settings:

Email Settings
--------------

.. _smtp.server:

smtp.server
^^^^^^^^^^^

Example::

  smtp.server = smtp.example.com:587

Default value: ``None``

The SMTP server to connect to when sending emails with optional port.

.. _smtp.starttls:

smtp.starttls
^^^^^^^^^^^^^

Example::

  smtp.starttls = True

Default value: ``None``

Whether or not to use STARTTLS when connecting to the SMTP server.

.. _smtp.user:

smtp.user
^^^^^^^^^

Example::

  smtp.user = username@example.com

Default value: ``None``

The username used to authenticate with the SMTP server.

.. _smtp.password:

smtp.password
^^^^^^^^^^^^^

Example::

  smtp.password = yourpass

Default value: ``None``

The password used to authenticate with the SMTP server.

.. _smtp.mail_from:

smtp.mail_from
^^^^^^^^^^^^^^

Example::

  smtp.mail_from = ckan@example.com

Default value: ``None``

The email address that emails sent by CKAN will come from. Note that, if left blank, the
SMTP server may insert its own.

.. _smtp.reply_to:

smtp.reply_to
^^^^^^^^^^^^^

Example::

  smtp.mail_from = noreply.example.com

Default value: ``None``

The email address that will be used if someone attempts to reply to a system email.
If left blank, no ``Reply-to`` will be added to the email and the value of
``smtp.mail_from`` will be used.

.. _email_to:

email_to
^^^^^^^^

Example::

  email_to = errors@example.com

Default value: ``None``

This controls where the error messages will be sent to.

.. _error_email_from:

error_email_from
^^^^^^^^^^^^^^^^

Example::

  error_email_from = ckan-errors@example.com

Default value: ``None``

This controls from which email the error messages will come from.
