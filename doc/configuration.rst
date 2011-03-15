CKAN Configuration
==================

A CKAN instance is configured with the .ini file in the root ckan directory. The most important parameter to set is the `sqlalchemy.url` giving the database connection. But there are also several additional options to change the way the CKAN site operates.

On a production machine the file will be probably be named after the site name. e.g. `ca.ckan.net.ini` On a development machine it is probably `development.ini`

On a new installation of ckan, you have to create a new config file from the template, something like this::

  paster --plugin ckan make-config ckan ca.ckan.net.ini

This creates ca.ckan.net.ini based on the template for this file in ckan/config/deployment.ini_tmpl

There are several general Pylons options, and all the CKAN-specific ones are in the `[app:main]` section.

Once the config file is changed, Apache needs to be restarted to read in the new changes.


sqlalchemy.url
--------------

Example::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantest3

This defines the database that CKAN is to use. The format is::

 sqlalchemy.url = postgres://USERNAME:PASSWORD@HOST/DBNAME


package_form
------------

Example::

 package_form = ca

Default value:  ``standard``

This sets the name of the form to use when editing a package. This can be a form defined in the core CKAN code or in another setuputils-managed python module. The only requirement is that the setup.py has an entrypoint for the form defined in the `ckan.forms` section. See :doc:`forms`


package_hide_extras
-------------------

Example::

 package_hide_extras = my_private_field other_field

Default value:  (empty)

This sets a space-seperated list of extra field key values which will not be shown on the package read page. While this is useful to create internal notes etc., it is not a security measure in any way. The keys will 
still be available via the API and in revision diffs. 


rdf_packages
------------

Example::

 rdf_packages = http://semantic.ckan.net/package/

Configure this if you have an RDF store of the same packages as are in your CKAN instance. It will provide three sorts of links from each package page to the equivalent RDF URL given in `rdf_packages`:

1. 303 redirects for clients that content-negotiate rdf-xml. e.g. client GETs `http://ckan.net/package/pollution-2008` with accept header `application/rdf+xml`. CKAN's response is a 303 redirect to `http://semantic.ckan.net/package/pollution-2008`

2. Embedded links for browsers that are aware. e.g. `<link rel="alternate" type="application/rdf+xml" href="http://semantic.ckan.net/package/pollution-2008">`

3. A visible RDF link on the page in the 'Alternative metadata formats' box. e.g. `<a href="http://semantic.ckan.net/package/pollution-2008">`


cache_enabled
-------------

Example::

 cache_enabled = True

Default value:  ``False``

Setting this option to True turns on several caches. When the caching is on, caching can be further configured as follows.

To set the type of Beaker storage::
 
 beaker.cache.type = file

To set the expiry times (in seconds) for specific controllers (which use the proxy_cache) specifiy the methods like this::

 ckan.controllers.package.list.expires = 600
 ckan.controllers.tag.read.expires = 600
 ckan.controllers.apiv1.package.list.expires = 600
 ckan.controllers.apiv1.package.show.expires = 600
 ckan.controllers.apiv2.package.list.expires = 600
 ckan.controllers.apiv2.package.show.expires = 600


openid_enabled
-------------

Example::

 openid_enabled = False

Default value:  ``True``

Setting this option to Fase turns off openid for login.


licenses_group_url
------------------

A url pointing to a JSON file containing a list of license objects. This list
determines the licenses offered by the system to users, for example when
creating or editing a package.

This is entirely optional -- by default the system will use the ckan list of
licenses available in the Licenses package.

.. _licenses python package: http://pypi.python.org/pypi/licenses

More details about the license objects including the license format and some
example license lists can be found on the open license service at
http://licenses.opendefinition.org/.

Examples::
 
 licenses_group_url = file:///path/to/my/local/json-list-of-licenses.js
 licenses_group_url = http://licenses.opendefinition.org/2.0/ckan_original


lang
----

Example::

 lang=de

Default value:  ``en`` (English)

Use this to specify the language of the text displayed in the CKAN web UI. This requires a suitable `mo` file installed for the language. For more information on internationalization, see: http://wiki.okfn.org/ckan/i18n#DeployingaTranslation


extra_template_paths
--------------------

Example::

 extra_template_paths=/home/okfn/brazil_ckan_config/templates

To customise the display of CKAN you can supply replacements for the Genshi template files. Use this option to specify where CKAN should look for them, before reverting to the 'ckan/templates' folder. You can supply more than one folder, separating the paths with a comma (,).

The example value for the extra_template_paths option could, for example, be used to override CKAN templates with these ones:

 * /home/okfn/brazil_ckan_config/templates/layout.html
 * /home/okfn/brazil_ckan_config/templates/package/edit.html

More details about this feature are found at: http://wiki.okfn.org/ckan/doc/theme


extra_public_paths
------------------

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for staticly served files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for them, before reverting to the 'ckan/public' folder. You can supply more than one folder, separating the paths with a comma (,).

The example value for the extra_public_paths option could, for example, be used to provide an image and stylesheet:

 * /home/okfn/brazil_ckan_config/public/images/brazil.png
 * /home/okfn/brazil_ckan_config/public/css/extra.css

More details about this feature are found at: http://wiki.okfn.org/ckan/doc/theme


package_new_return_url & package_edit_return_url
------------------------------------------------

Example::

 package_new_return_url = http://datadotgc.ca/new_dataset_complete?name=<NAME>
 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

To allow the Edit Package and New Package forms to be integrated into a third party interface, setting these options allows you to set a the return address. So when the user has completed the form and presses 'commit', the user is redirected to the URL specified.

The '<NAME>' string is replaced with the name of the package edited. Full details of this process are given in :doc:`form-integration`.


carrot_messaging_library
------------------------

Example::

 carrot_messaging_library=pyamqplib

This is the messaging library backend to use. Options::

 * ``pyamqplib`` - AMQP (e.g. for RabbitMQ)

 * ``pika`` - alternative AMQP

 * ``stomp`` - python-stomp

 * ``queue`` - native Python Queue (default) - NB this doesn't work inter-process

See `carrot documentation <http://packages.python.org/carrot/index.html>`_ for details.


amqp_hostname, amqp_port, amqp_user_id, amqp_password
-----------------------------------------------------

Example::

 amqp_hostname=localhost
 amqp_port=5672
 amqp_user_id=guest
 amqp_password=guest

These are the setup parameters for AMQP messaging. These only apply if the messageing library has been set to use AMQP (see `carrot_messaging_library`_). The values given in the example are the default values.


build_search_index_synchronously
--------------------------------

Example::

 ckan.build_search_index_synchronously=

Default (if you don't define it)::
 indexing is on

This controls the operation of the CKAN Postgres full text search indexing. If you don't define this option then indexing is on. You will want to turn this off if you want to use a different search engine for CKAN (e.g. SOLR). In this case you need to define the option equal to blank (as in the given example).


search_backend
--------------

Example::

 search_backend = solr

Default value:  ``sql``

This controls the type of search backend. Currently valid values are ``sql`` (meaning Postgres full text search) and ``solr``. If you specify ``sql`` then ensure indexing is on (`build_search_index_synchronously`_ is not defined). If you specify ``solr`` then ensure you specify a `solr_url`_.


solr_url
--------

Example::

 solr_url = http://solr.okfn.org/solr/test.ckan.net
 
This configures SOLR search, (if selected with 'search_backend'_). Running solr will require a schema.xml file, such as the one
in `the ckan-solr-index repository <http://bitbucket.org/pudo/ckan-solr-index>`_.

Optionally, ``solr_user`` and ``solr_password`` can also be passed along to specify HTTP Basic authentication details for all solr requests. 


site_title
----------

Example::

 ckan.site_title=Open Data Scotland

Default value:  ``CKAN``

This sets the name of the site, as displayed in the CKAN web interface.


site_description
----------------

Example::

 ckan.site_description=

Default value:  (none)

This is for a description, or tag line for the site, as displayed in the header of the CKAN web interface.


site_logo
---------

Example::

 ckan.site_logo=/images/ckan_logo_fullname_long.png

Default value:  (none)

This sets the logo used in the title bar.


site_url
--------

Example::

 ckan.site_url=http://scotdata.ckan.net

Default value:  (none)

The primary URL used by this site. Uses::

 * in the API to provide packages with links to themselves in the web UI.


api_url
--------

Example::

 ckan.api_url=http://scotdata.ckan.net/api

Default value:  ``/api``

The URL which resolves to the CKAN API part of the site. This is useful if the
API is hosted on a different domain, for example when a third party site uses
the forms API.

default_roles
-------------

This allows you to set the default authorization roles (i.e. permissions) for new objects. Currently this extends to new packages, groups, authorization groups and the 'system' object. For full details of these, see :doc:`authorization`.

The value is a strict JSON dictionary of user names "visitor" and "logged_in" with lists of their roles.

Example::

 ckan.default_roles.Package = {"visitor": ["reader"], "logged_in": ["reader"]}

With this example setting, visitors (any user who is not logged in) and logged in users can only read packages that get created (only sysadmins can edit).

Defaults::

 ckan.default_roles.Package = {"visitor": ["editor"], "logged_in": ["editor"]}
 ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["reader"]}
 ckan.default_roles.System = {"visitor": ["reader"], "logged_in": ["editor"]}
 ckan.default_roles.AuthorizationGroup = {"visitor": ["reader"], "logged_in": ["reader"]}
