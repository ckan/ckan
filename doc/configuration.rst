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

 ckan.site_logo = /images/ckan_logo_fullname_long.png

Default value:  (none)

This sets the logo used in the title bar.

.. index::
   single: site_url


.. index::
   single: package_hide_extras

favicon
^^^^^^^

Example::

 ckan.favicon = http://okfn.org/wp-content/themes/okfn-master-wordpress-theme/images/favicon.ico

Default value: ``/images/icons/ckan.ico``

This sets the site's `favicon`. This icon is usually displayed by the browser in the tab heading and bookmark.

site_about
^^^^^^^^^^

Example::

 ckan.site_about=${g.site_title} is a community-driven catalogue of open data for the Greenfield area.

Default value::

 What was the <a href="http://thedatahub.org/dataset/house-prices-uk-from-1930">average price</a> of a house in the UK in 1935? When will India's projected population <a href="http://thedatahub.org/dataset/guardian-population-unitednations">overtake</a> that of China? Where can you see <a href="http://thedatahub.org/dataset/seattle-public-art">publicly-funded art</a> in Seattle? Data to answer many, many questions like these is out there on the Internet somewhere - but it is not always easy to find.</p>

  <p i18n:msg="">${g.site_title} is a community-run catalogue of useful sets of data on the Internet. You can collect links here to data from around the web for yourself and others to use, or search for data that others have collected. Depending on the type of data (and its conditions of use), ${g.site_title} may also be able to store a copy of the data or host it in a database, and provide some basic visualisation tools.

This changes the text about the site on the 'About' page. i.e. replaces the text in the "About <site_name" section. The other sections of the About page are not affected.

Format tips:

 * multiline strings can be used by indenting following lines

 * the format is basically HTML, but with Genshi-format strings

 * the about text will be automatically be placed with-in paragraph tags ``<p>...</p>`` but you can start new paragraphs within that by using ``</p><p>``

.. note:: Whilst the default text is translated into many languages (switchable in the page footer), the text in this configuration option will not be translatable.

package_hide_extras
^^^^^^^^^^^^^^^^^^^

Example::

 package_hide_extras = my_private_field other_field

Default value:  (empty)

This sets a space-separated list of extra field key values which will not be shown on the dataset read page.

.. warning::  While this is useful to e.g. create internal notes, it is not a security measure. The keys will still be available via the API and in revision diffs.

.. index::
   single: rdf_packages

.. _config-apps-ideas:

ckan.dataset.show_apps_ideas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ckan.dataset.show_apps_ideas::

 ckan.dataset.show_apps_ideas = false

Default value:  true

When set to false, or no, this setting will hide the 'Apps, Ideas, etc' tab on the package read page. If the value is not set, or is set to true or yes, then the tab will shown.

rdf_packages
^^^^^^^^^^^^

Example::

 rdf_packages = http://semantic.ckan.net/record/

Configure this if you have an RDF store of the same datasets as are in your CKAN instance. It will provide three sorts of links from each dataset page to the equivalent RDF URL given in `rdf_packages`:

1. 303 redirects for clients that content-negotiate rdf-xml or turtle. e.g. client GETs `http://ckan.net/dataset/pollution-2008` with accept header `application/rdf+xml` ``curl -H "Accept: application/rdf+xml" http://ckan.net/dataset/pollution-2008``. CKAN's response is a 303 redirect to `http://semantic.ckan.net/dataset/pollution-2008` which can be obtained with: ``curl -L -H "Accept: application/rdf+xml" http://ckan.net/dataset/pollution-2008``

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

For more information on using dumpfiles, see :doc:`database-dumps`.

recaptcha
^^^^^^^^^

Example::
 ckan.recaptcha.publickey = 6Lc...-KLc
 ckan.recaptcha.privatekey = 6Lc...-jP

Setting both these options according to an established Recaptcha account adds captcha to the user registration form. This has been effective at preventing bots registering users and creating spam packages.

To get a Recaptcha account, sign up at: http://www.google.com/recaptcha

And there is an option for the default expiry time if not specified::

 ckan.cache.default_expires = 600


datasets_per_page
^^^^^^^^^^^^^^^^^

Example::

 ckan.datasets_per_page = 10

Default value:  ``20``

This controls the pagination of the dataset search results page. This is the maximum number of datasets viewed per page of results.


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
   single: ckan.locale_default

ckan.locale_default
^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_default=de

Default value:  ``en`` (English)

Use this to specify the locale (language of the text) displayed in the CKAN Web UI. This requires a suitable `mo` file installed for the locale in the ckan/i18n. For more information on internationalization, see :doc:`i18n`. If you don't specify a default locale, then it will default to the first locale offered, which is by default English (alter that with `ckan.locales_offered` and `ckan.locales_filtered_out`.

.. note: In versions of CKAN before 1.5, the settings used for this was variously `lang` or `ckan.locale`, which have now been deprecated in favour of `ckan.locale_default`.

ckan.locales_offered
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_offered=en de fr

Default value: (none)

By default, all locales found in the ckan/i18n directory will be offered to the user. To only offer a subset of these, list them under this option. The ordering of the locales is preserved when offered to the user.

ckan.locales_filtered_out
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_filtered_out=pl ru

Default value: (none)

If you want to not offer particular locales to the user, then list them here to have them removed from the options.

ckan.locale_order
^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_order=fr de

Default value: (none)

If you want to specify the ordering of all or some of the locales as they are offered to the user, then specify them here in the required order. Any locales that are available but not specified in this option, will still be offered at the end of the list.


Storage Settings
----------------

.. index::
   single: ckan.storage.bucket, ofs.storage_dir

ckan.storage.bucket
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.storage.bucket = ckan

Default value:  ``None``

This setting will change the bucket name for the uploaded files.

ofs.storage_dir
^^^^^^^^^^^^^^^

Example::

  ofs.storage_dir = /data/uploads/

Default value:  ``None``

Use this to specify where uploaded files should be stored, and also to turn on the handling of file storage. The folder should exist, and will automatically be turned into a valid pairtree repository if it is not already.



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

template_head_end
^^^^^^^^^^^^^^^^^

HTML content to be inserted just before ``</head>`` tag (e.g. extra stylesheet)

Example::

  ckan.template_head_end = <link rel="stylesheet" href="http://mysite.org/css/custom.css" type="text/css">

You can also have multiline strings. Just indent following lines. e.g.::

 ckan.template_head_end =
  <link rel="stylesheet" href="/css/extra1.css" type="text/css">
  <link rel="stylesheet" href="/css/extra2.css" type="text/css">

template_footer_end
^^^^^^^^^^^^^^^^^^^

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


Form Settings
-------------

.. index::
   single: package_form

package_form
^^^^^^^^^^^^

Example::

 package_form = ca

Default value:  ``standard``

This sets the name of the Formalchemy form to use when editing a dataset.

.. note:: This setting only applies to the deprecated Formalchemy forms. For enabling forms defined with a Navl schema, see :doc:`forms`.

The value for this setting can be a Formalchemy form defined in the core CKAN code or in another setuputils-managed python module. The only requirement is that the ``setup.py`` file has an entry point for the form defined in the ``ckan.forms`` section.

For more information on forms, see :doc:`forms`.

.. index::
   single: package_new_return_url, package_edit_return_url

.. _config-package-urls:

package_new_return_url & package_edit_return_url
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 package_new_return_url = http://datadotgc.ca/new_dataset_complete?name=<NAME>
 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

If integrating the Edit Dataset and New Dataset forms into a third-party interface, setting these options allows you to set the return address. When the user has completed the form and presses 'commit', the user is redirected to the URL specified.

The ``<NAME>`` string is replaced with the name of the dataset edited. Full details of this process are given in :doc:`form-integration`.


.. index::
   single: licenses_group_url

licenses_group_url
^^^^^^^^^^^^^^^^^^

A url pointing to a JSON file containing a list of licence objects. This list
determines the licences offered by the system to users, for example when
creating or editing a dataset.

This is entirely optional - by default, the system will use an internal cached
version of the CKAN list of licences available from the
http://licenses.opendefinition.org/licenses/groups/ckan.json.

More details about the license objects - including the licence format and some
example licence lists - can be found at the `Open Licenses Service
<http://licenses.opendefinition.org/>`_.

Examples::

 licenses_group_url = file:///path/to/my/local/json-list-of-licenses.json
 licenses_group_url = http://licenses.opendefinition.org/licenses/groups/od.json


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
   single: ckan.site_id

ckan.site_id
^^^^^^^^^^^^

Example::

 ckan.site_id = my_ckan_instance

CKAN uses Solr to index and search packages. The search index is linked to the value of the ``ckan.site_id``, so if you have more than one
CKAN instance using the same `solr_url`_, they will each have a separate search index as long as their ``ckan.site_id`` values are different. If you are only running
a single CKAN instance then this can be ignored.

Note, if you change this value, you need to rebuild the search index.

.. index::
   single: solr_url

.. _solr_url:

solr_url
^^^^^^^^

Example::

 solr_url = http://solr.okfn.org:8983/solr/ckan-schema-1.3

Default value:  ``http://solr.okfn.org:8983/solr``

This configures the Solr server used for search. The Solr schema found at that URL must be one of the ones in ``ckan/config/solr`` (generally the most recent one). A check of the schema version number occurs when CKAN starts.

Optionally, ``solr_user`` and ``solr_password`` can also be configured to specify HTTP Basic authentication details for all Solr requests.

Note, if you change this value, you need to rebuild the search index.

.. index::
   single: ckan.search.automatic_indexing

ckan.search.automatic_indexing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.automatic_indexing = 1

Make all changes immediately available via the search after editing or
creating a dataset. Default is true. If for some reason you need the indexing
to occur asynchronously, set this option to 0.

Note, this is equivalent to explicitly load the `synchronous_search` plugin.


simple_search
^^^^^^^^^^^^^

Example::

 ckan.simple_search = true

Default value:  ``false``

Switching this on tells CKAN search functionality to just query the database, (rather than using Solr). In this setup, search is crude and limited, e.g. no full-text search, no faceting, etc. However, this might be very useful for getting up and running quickly with CKAN.


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

The primary URL used by this site. Used in the API to provide datasets with links to themselves in the web UI.

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

apikey_header_name
^^^^^^^^^^^^^^^^^^

Example::

 apikey_header_name = API-KEY

Default value: ``X-CKAN-API-Key`` & ``Authorization``

This allows another http header to be used to provide the CKAN API key. This is useful if network infrastructure block the Authorization header and ``X-CKAN-API-Key`` is not suitable.

Authorization Settings
----------------------

.. index::
   single: default_roles, auth_profile

default_roles
^^^^^^^^^^^^^

This allows you to set the default authorization roles (i.e. permissions) for new objects. Currently this extends to new datasets, groups, authorization groups and the ``system`` object. For full details of these, see :doc:`authorization`.

The value is a strict JSON dictionary of user names ``visitor`` (any user who is not logged in)  and ``logged_in`` (any user who is logged in) with lists of their roles.

Example::

 ckan.default_roles.Package = {"visitor": ["editor"], "logged_in": ["editor"]}
 ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["reader"]}

With this example setting, visitors and logged-in users can only read datasets that get created.

Defaults: see in ``ckan/model/authz.py`` for: ``default_default_user_roles``

Plugin Settings
---------------

.. index::
   single: plugins

plugins
^^^^^^^

Example::

  ckan.plugins = disqus datapreview googleanalytics follower

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



Compatibility
-------------

.. index::
   single: restrict_template_vars

restrict_template_vars
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.restrict_template_vars = true

Default value:  ``false``

This is used to limit the functions available via h in templates.  It also forces correct usage of functions as some function signatures have changed.  It's main purpose is to allow transition to a cleaner world.
