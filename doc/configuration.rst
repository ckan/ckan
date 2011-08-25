.. index::
   single: config file

=====================================
Reference: CKAN Configuration Options
=====================================

You can change many important CKAN settings in the CKAN config file. This is the file called ``std.ini`` that you first encountered in :ref:`create-admin-user`. It is usually located at ``/etc/ckan/std/std.ini``.

The file is well-documented, but we recommend reading this section in full to learn about the CKAN config options available to you. 

.. note:: After editing this file, you will need to restart Apache for the changes to take effect. 

.. note:: The CKAN config file also includes general Pylons options. All CKAN-specific settings are in the `[app:main]` section.

Database Settings
-----------------

.. index::
   single: sqlalchemy.url

sqlalchemy.url
^^^^^^^^^^^^^^

Example::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantest3

This defines the database that CKAN is to use. The format is::

 sqlalchemy.url = postgres://USERNAME:PASSWORD@HOST/DBNAME


Front-End Settings
------------------


.. index::
   single: site_description

site_description
^^^^^^^^^^^^^^^^

Example::

 ckan.site_description=

Default value:  (none)

This is for a description, or tag line for the site, as displayed in the header of the CKAN web interface.

.. index::
   single: site_logo

site_logo
^^^^^^^^^

Example::

 ckan.site_logo=/images/ckan_logo_fullname_long.png

Default value:  (none)

This sets the logo used in the title bar.

.. index::
   single: site_url


.. index::
   single: package_hide_extras

package_hide_extras
^^^^^^^^^^^^^^^^^^^

Example::

 package_hide_extras = my_private_field other_field

Default value:  (empty)

This sets a space-separated list of extra field key values which will not be shown on the package read page. 

.. warning::  While this is useful to e.g. create internal notes, it is not a security measure. The keys will still be available via the API and in revision diffs. 

.. index::
   single: rdf_packages

rdf_packages
^^^^^^^^^^^^

Example::

 rdf_packages = http://semantic.ckan.net/record/

Configure this if you have an RDF store of the same packages as are in your CKAN instance. It will provide three sorts of links from each package page to the equivalent RDF URL given in `rdf_packages`:

1. 303 redirects for clients that content-negotiate rdf-xml or turtle. e.g. client GETs `http://ckan.net/package/pollution-2008` with accept header `application/rdf+xml` ``curl -H "Accept: application/rdf+xml" http://ckan.net/package/pollution-2008``. CKAN's response is a 303 redirect to `http://semantic.ckan.net/package/pollution-2008` which can be obtained with: ``curl -L -H "Accept: application/rdf+xml" http://ckan.net/package/pollution-2008``

2. Embedded links for browsers that are aware. e.g. `<link rel="alternate" type="application/rdf+xml" href="http://semantic.ckan.net/record/b410e678-8a96-40cf-8e46-e8bd4bf02684.rdf">`

3. A visible RDF link on the page. e.g. `<a href="http://semantic.ckan.net/record/b410e678-8a96-40cf-8e46-e8bd4bf02684.rdf">`

.. index::
   single: dumps_url, dumps_format

dumps_url & dumps_format
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.dumps_url = http://ckan.net/dump/
  ckan.dumps_format = CSV/JSON

If there is a page which allows you to download a dump of the entire catalogue then specify the URL and the format here, so that it can be advertised in the web interface. ``dumps_format`` is just a string for display.

For more information on using dumpfiles, see :doc:`database_dumps`.


Cache Settings
--------------

.. index::
   single: cache_validation_enabled

cache_validation_enabled
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.cache_validation_enabled = False

Default value:  ``True``

This option determines whether browsers (or other caching services running between the browser and CKAN) are helped to cache particular CKAN pages, by validating when the page content hasn't changed. This is achieved using ETag headers provided by CKAN, which is a hash that changes when the content has changed. 

Developers editing the templates should set this to False, since ETag hashes don't look for template changes.

.. index::
   single: cache_enabled

cache_enabled
^^^^^^^^^^^^^

Example::

 ckan.cache_enabled = True

Default value:  ``False``

Setting this option to True turns on several server-side caches. When caching is on, caching can be further configured as follows. 

To set the type of Beaker storage::
 
 beaker.cache.type = file

To set the expiry times (in seconds) for specific controllers (which use the proxy_cache) specify the methods like this::

 ckan.controllers.package.list.expires = 600
 ckan.controllers.tag.read.expires = 600
 ckan.controllers.apiv1.package.list.expires = 600
 ckan.controllers.apiv1.package.show.expires = 600
 ckan.controllers.apiv2.package.list.expires = 600
 ckan.controllers.apiv2.package.show.expires = 600

There is also an option to set the max-age value of static files delivered by paster::

 ckan.static_max_age = 3600


Authentication Settings
-----------------------

.. index::
   single: openid_enabled

openid_enabled
^^^^^^^^^^^^^^

Example::

 openid_enabled = False

Default value:  ``True``

CKAN operates a delegated authentication model based on `OpenID <http://openid.net/>`_.

Setting this option to False turns off OpenID for login.


.. _config-i18n:

Internationalisation Settings
-----------------------------

.. index::
   single: lang

lang
^^^^

Example::

 lang=de

Default value:  ``en`` (English)

Use this to specify the language of the text displayed in the CKAN web UI. This requires a suitable `mo` file installed for the language. For more information on internationalization, see :doc:`i18n`.

Theming Settings
----------------

.. index::
   single: extra_template_paths

extra_template_paths
^^^^^^^^^^^^^^^^^^^^

Example::

 extra_template_paths=/home/okfn/brazil_ckan_config/templates

To customise the display of CKAN you can supply replacements for the Genshi template files. Use this option to specify where CKAN should look for additional templates, before reverting to the ``ckan/templates`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.

.. index::
   single: extra_public_paths

extra_public_paths
^^^^^^^^^^^^^^^^^^

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for static files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for additional files, before reverting to the ``ckan/public`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.


Form Settings
-------------

.. index::
   single: package_form

package_form
^^^^^^^^^^^^

Example::

 package_form = ca

Default value:  ``standard``

This sets the name of the form to use when editing a package. This can be a form defined in the core CKAN code or in another setuputils-managed python module. The only requirement is that the ``setup.py`` file has an entry point for the form defined in the ``ckan.forms`` section. 

For more information on forms, see :doc:`forms`.

.. _config-package-urls:

.. index::
   single: package_new_return_url, package_edit_return_url

package_new_return_url & package_edit_return_url
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 package_new_return_url = http://datadotgc.ca/new_dataset_complete?name=<NAME>
 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

If integrating the Edit Package and New Package forms into a third-party interface, setting these options allows you to set the return address. When the user has completed the form and presses 'commit', the user is redirected to the URL specified.

The ``<NAME>`` string is replaced with the name of the package edited. Full details of this process are given in :doc:`form-integration`.


.. index::
   single: licenses_group_url

licenses_group_url
^^^^^^^^^^^^^^^^^^

A url pointing to a JSON file containing a list of licence objects. This list
determines the licences offered by the system to users, for example when
creating or editing a package.

This is entirely optional - by default, the system will use the CKAN list of
licences available in the `Python licenses package <http://pypi.python.org/pypi/licenses>`_.

More details about the CKAN license objects - including the licence format and some
example licence lists - can be found at the `Open Licenses Service 
<http://licenses.opendefinition.org/>`_.

Examples::
 
 licenses_group_url = file:///path/to/my/local/json-list-of-licenses.js
 licenses_group_url = http://licenses.opendefinition.org/2.0/ckan_original


Messaging Settings
------------------

.. index::
   single: carrot_messaging_library

carrot_messaging_library
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 carrot_messaging_library=pyamqplib

This is the messaging library backend to use. Options::

 * ``pyamqplib`` - AMQP (e.g. for RabbitMQ)

 * ``pika`` - alternative AMQP

 * ``stomp`` - python-stomp

 * ``queue`` - native Python Queue (default) - NB this doesn't work inter-process

See the `Carrot documentation <http://packages.python.org/carrot/index.html>`_ for details.

.. index::
   single: amqp_hostname, amqp_port, amqp_user_id, amqp_password

amqp_hostname, amqp_port, amqp_user_id, amqp_password
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 amqp_hostname=localhost
 amqp_port=5672
 amqp_user_id=guest
 amqp_password=guest

These are the setup parameters for AMQP messaging. These only apply if the messaging library has been set to use AMQP (see `carrot_messaging_library`_). The values given above are the default values.

Search Settings
---------------

.. index::
   single: build_search_index_synchronously

build_search_index_synchronously
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.build_search_index_synchronously=

or::

 ckan.plugins = synchronous_search

Default (if you don't define it)::
 indexing is on

This controls the operation of the CKAN Postgres full text search indexing. If you don't define this option then indexing is on. You will want to turn this off if you want to use a different search engine for CKAN (e.g. Solr). In this case you need to define the option equal to blank (as in the example).

.. index::
   single: ckan.site_id

ckan.site_id
^^^^^^^^^^^^

Example::

 ckan.site_id = my_ckan_instance

CKAN uses Solr to index and search packages. The search index is linked to the value of the ``ckan.site_id``, so if you have more than one
CKAN instance using the same `solr_url`_, they will each have a separate search index as long as their ``ckan.site_id`` values are different. If you are only running
a single CKAN instance then this can be ignored.

.. index::
   single: solr_url

solr_url
^^^^^^^^

Example::

 solr_url = http://solr.okfn.org/solr/test.ckan.net
 
This configures Solr search (if selected with `search_backend`_). Running Solr will require a schema.xml file, such as the one in `the ckanext-solr repository <https://bitbucket.org/okfn/ckanext-solr/src>`_.

Optionally, ``solr_user`` and ``solr_password`` can also be passed along to specify HTTP Basic authentication details for all Solr requests. 

.. index::
   single: search_enabled

search_enabled
^^^^^^^^^^^^^^

Example::

 search_enabled = False
 
Optional. Default = True.

This allows you to hide the search widgets and disables indexing of packages if it is set to False.


Site Settings
-------------

.. index::
   single: site_title

site_title
^^^^^^^^^^

Example::

 ckan.site_title=Open Data Scotland

Default value:  ``CKAN``

This sets the name of the site, as displayed in the CKAN web interface.

.. index::
   single: site_url

site_url
^^^^^^^^

Example::

 ckan.site_url=http://scotdata.ckan.net

Default value:  (none)

The primary URL used by this site. Used in the API to provide packages with links to themselves in the web UI.

.. index::
   single: api_url

api_url
^^^^^^^

Example::

 ckan.api_url=http://scotdata.ckan.net/api

Default value:  ``/api``

The URL that resolves to the CKAN API part of the site. This is useful if the
API is hosted on a different domain, for example when a third-party site uses
the forms API.


Authorization Settings
----------------------

.. index::
   single: default_roles

default_roles
^^^^^^^^^^^^^

This allows you to set the default authorization roles (i.e. permissions) for new objects. Currently this extends to new packages, groups, authorization groups and the ``system`` object. For full details of these, see :doc:`authorization`.

The value is a strict JSON dictionary of user names ``visitor`` (any user who is not logged in)  and ``logged_in`` (any user who is logged in) with lists of their roles.

Example::

 ckan.default_roles.Package = {"visitor": ["editor"], "logged_in": ["editor"]}
 ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["reader"]}

With this example setting, visitors and logged-in users can only read packages that get created.

Defaults: see in ``ckan/model/authz.py`` for: ``default_default_user_roles``


Plugin Settings
---------------

.. index::
   single: plugins

plugins
^^^^^^^

Example::

  ckan.plugins = disqus synchronous_search datapreview googleanalytics stats storage admin follower

Specify which CKAN extensions are to be enabled. 

.. warning::  If you specify an extension but have not installed the code,  CKAN will not start. 

Format as a space-separated list of the extension names. The extension name is the key in the [ckan.plugins] section of the extension's ``setup.py``. For more information on extensions, see :doc:`extensions`.



Directory Settings
------------------

.. index::
   single: log_dir

log_dir
^^^^^^^

Example::

  ckan.log_dir = /var/log/ckan/

This is the directory to which CKAN cron scripts (if there are any installed) should write log files. 

.. note::  This setting is nothing to do with the main CKAN log file, whose filepath is set in the ``[handler_file]`` args.

.. index::
   single: dump_dir

dump_dir
^^^^^^^^

Example::

  ckan.dump_dir = /var/lib/ckan/dump/

This is the directory to which JSON or CSV dumps of the database are to be written, assuming a script has been installed to do this. 

.. note::  It is usual to set up the Apache config to serve this directory.

.. index::
   single: backup_dir

backup_dir
^^^^^^^^^^

Example::

  ckan.backup_dir = /var/backups/ckan/

This is a directory where SQL database backups are to be written, assuming a script has been installed to do this.
