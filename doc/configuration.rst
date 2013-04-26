=====================================
Reference: CKAN Configuration Options
=====================================

You can change many important CKAN settings in the CKAN config file. This is the file called ``std.ini`` that you first encountered in :ref:`create-admin-user`. It is usually located at ``/etc/ckan/std/std.ini``.

The file is well-documented, but we recommend reading this section in full to learn about the CKAN config options available to you.

.. note:: After editing this file, you will need to restart Apache for the changes to take effect.

.. note:: The CKAN config file also includes general Pylons options. All CKAN-specific settings are in the `[app:main]` section.


Database Settings
-----------------

sqlalchemy.url
^^^^^^^^^^^^^^

Example::

 sqlalchemy.url = postgres://tester:pass@localhost/ckantest3

This defines the database that CKAN is to use. The format is::

 sqlalchemy.url = postgres://USERNAME:PASSWORD@HOST/DBNAME


Front-End Settings
------------------

.. _ckan-site-title:

ckan.site_title
^^^^^^^^^^^^^^^

Example::

 ckan.site_title = Open Data Scotland

Default value:  ``CKAN``

This sets the name of the site, as displayed in the CKAN web interface.

ckan.site_description
^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.site_description = The easy way to get, use and share data

Default value:  (none)

This is for a description, or tag line for the site, as displayed in the header of the CKAN web interface.

ckan.site_intro_text
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.site_intro_text = Nice introductory paragraph about CKAN or the site in general.

Default value:  (none)

This is for an introductory text used in the default template's index page.

ckan.site_logo
^^^^^^^^^^^^^^

Example::

 ckan.site_logo = /images/ckan_logo_fullname_long.png

Default value:  (none)

This sets the logo used in the title bar.

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
          For this reason, it's better to overload the snippet in ``home/snippets/about_text.html``. For more information, see :doc:`theming`.

ckan.main_css
^^^^^^^^^^^^^

Example::

  ckan.main_css = /base/css/my-custom.css

Default value: ``/base/css/main.css``

With this option, instead of using the default `main.css`, you can use your own.

ckan.favicon
^^^^^^^^^^^^

Example::

 ckan.favicon = http://okfn.org/wp-content/themes/okfn-master-wordpress-theme/images/favicon.ico

Default value: ``/images/icons/ckan.ico``

This sets the site's `favicon`. This icon is usually displayed by the browser in the tab heading and bookmark.

ckan.datasets_per_page
^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.datasets_per_page = 10

Default value:  ``20``

This controls the pagination of the dataset search results page. This is the maximum number of datasets viewed per page of results.

package_hide_extras
^^^^^^^^^^^^^^^^^^^

Example::

 package_hide_extras = my_private_field other_field

Default value:  (empty)

This sets a space-separated list of extra field key values which will not be shown on the dataset read page.

.. warning::  While this is useful to e.g. create internal notes, it is not a security measure. The keys will still be available via the API and in revision diffs.

.. _config-apps-ideas:

ckan.dataset.show_apps_ideas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ckan.dataset.show_apps_ideas::

 ckan.dataset.show_apps_ideas = false

Default value:  true

When set to false, or no, this setting will hide the 'Apps, Ideas, etc' tab on the package read page. If the value is not set, or is set to true or yes, then the tab will shown.

.. note::  This only applies to the legacy Genshi-based templates


ckan.activity_list_limit
^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.activity_list_limit = 31

Default value: ``infinite``

This controls the number of activities to show in the Activity Stream. By default, it shows everything.

ckan.preview.direct
^^^^^^^^^^^^^^^^^^^

Example::
 ckan.preview.direct = png jpg gif

Default value: ``png jpg gif``

Defines the resource formats which should be embedded directly in an ``img`` tag
when previewing them.

ckan.preview.loadable
^^^^^^^^^^^^^^^^^^^^^

Example::
 ckan.preview.loadable = html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom rss txt

Default value: ``html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom rss txt``

Defines the resource formats which should be loaded directly in an ``iframe``
tag when previewing them.

ckan.dumps_url & ckan.dumps_format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.dumps_url = http://ckan.net/dump/
  ckan.dumps_format = CSV/JSON

If there is a page which allows you to download a dump of the entire catalogue then specify the URL and the format here, so that it can be advertised in the web interface. ``dumps_format`` is just a string for display.

For more information on using dumpfiles, see :doc:`database-dumps`.

ckan.recaptcha.publickey & ckan.recaptcha.privatekey
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::
 ckan.recaptcha.publickey = 6Lc...-KLc
 ckan.recaptcha.privatekey = 6Lc...-jP

Setting both these options according to an established Recaptcha account adds captcha to the user registration form. This has been effective at preventing bots registering users and creating spam packages.

To get a Recaptcha account, sign up at: http://www.google.com/recaptcha

ckan.feeds.author_name
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.author_name = Michael Jackson

Default value: ``(none)``

This controls the feed author's name. If unspecified, it'll use :ref:`ckan-site-id`.

ckan.feeds.author_link
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.author_link = http://okfn.org

Default value: ``(none)``

This controls the feed author's link. If unspecified, it'll use :ref:`ckan-site-url`.

ckan.feeds.authority_name
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.feeds.authority_name = http://okfn.org

Default value: ``(none)``

The domain name or email address of the default publisher of the feeds and elements. If unspecified, it'll use :ref:`ckan-site-url`.

ckan.feeds.date
^^^^^^^^^^^^^^^

Example::

  ckan.feeds.date = 2012-03-22

Default value: ``(none)``

A string representing the default date on which the authority_name is owned by the publisher of the feed.

ckan.featured_groups
^^^^^^^^^^^^^^^^^^^^

Example::
 ckan.featured_groups = group_one group_two

Default Value: (empty)

Defines a list of group names or group ids. This setting is used to display
groups and datasets from each group on the home page in the default templates
(2 groups and 2 datasets for each group are displayed).

Authentication Settings
-----------------------

ckan.gravatar_default
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.gravatar_default = monsterid

Default value: ``identicon``

This controls the default gravatar avatar, in case the user has none.

ckan.legacy_templates
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.legacy_templates = True

Default value: ``False``

This controls if the legacy genshi templates are used.

.. note:: This is only for legacy code, and shouldn't be used anymore.


Activity Streams Settings
-------------------------

ckan.activity_streams_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.activity_streams_enabled = False

Default value:  ``True``

Turns on and off the activity streams used to track changes on datasets, groups, users, etc

.. _ckan-activity-streams-email-notifications:

ckan.activity_streams_email_notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.activity_streams_email_notifications = False

Default value:  ``False``

Turns on and off the activity streams' email notifications. You'd also need to setup a cron job to send
the emails. For more information, visit :ref:`email-notifications`.


.. _config-i18n:

Internationalisation Settings
-----------------------------

ckan.locale_default
^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_default = de

Default value:  ``en`` (English)

Use this to specify the locale (language of the text) displayed in the CKAN Web UI. This requires a suitable `mo` file installed for the locale in the ckan/i18n. For more information on internationalization, see :doc:`i18n`. If you don't specify a default locale, then it will default to the first locale offered, which is by default English (alter that with `ckan.locales_offered` and `ckan.locales_filtered_out`.

.. note: In versions of CKAN before 1.5, the settings used for this was variously `lang` or `ckan.locale`, which have now been deprecated in favour of `ckan.locale_default`.

ckan.locales_offered
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_offered = en de fr

Default value: (none)

By default, all locales found in the ``ckan/i18n`` directory will be offered to the user. To only offer a subset of these, list them under this option. The ordering of the locales is preserved when offered to the user.

ckan.locales_filtered_out
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.locales_filtered_out = pl ru

Default value: (none)

If you want to not offer particular locales to the user, then list them here to have them removed from the options.

ckan.locale_order
^^^^^^^^^^^^^^^^^

Example::

 ckan.locale_order = fr de

Default value: (none)

If you want to specify the ordering of all or some of the locales as they are offered to the user, then specify them here in the required order. Any locales that are available but not specified in this option, will still be offered at the end of the list.

ckan.i18n_directory
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.i18n_directory = /opt/locales/i18n/

Default value: (none)

By default, the locales are searched for in the ``ckan/i18n`` directory. Use this option if you want to use another folder.

.. _ckan_root_path:

ckan.root_path
^^^^^^^^^^^^^^

Example::

  ckan.root_path = /my/custom/path/{{LANG}}/foo

Default value: (none)

By default, the URLs are formatted as ``/some/url``, when using the default
locale, or ``/de/some/url`` when using the "de" locale, for example. This
lets you change this. You can use any path that you want, adding ``{{LANG}}``
where you want the locale code to go.


Storage Settings
----------------

ckan.storage.bucket
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.storage.bucket = ckan

Default value:  ``None``

This setting will change the bucket name for the uploaded files.

ckan.storage.key_prefix
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.storage.key_prefix = ckan-file/

Default value: ``file/``

This setting will change the prefix for the uploaded files.

ckan.storage.max_content_length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.storage.max_content_length = 500000

Default value: ``50000000``

This defines the maximum content size, in bytes, for uploads.

ofs.storage_dir
^^^^^^^^^^^^^^^

Example::

  ofs.storage_dir = /data/uploads/

Default value:  ``None``

Use this to specify where uploaded files should be stored, and also to turn on the handling of file storage. The folder should exist, and will automatically be turned into a valid pairtree repository if it is not already.

ckan.cache_enabled
^^^^^^^^^^^^^^^^^^

Example::

  ckan.cache_enabled = True

Default value: ``None``

Controls if we're caching CKAN's static files, if it's serving them.

ckan.static_max_age
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.static_max_age = 2592000

Default value: ``3600``

Controls CKAN static files' cache max age, if we're serving and caching them.


Theming Settings
----------------

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

extra_template_paths
^^^^^^^^^^^^^^^^^^^^

Example::

 extra_template_paths = /home/okfn/brazil_ckan_config/templates

To customise the display of CKAN you can supply replacements for the Genshi template files. Use this option to specify where CKAN should look for additional templates, before reverting to the ``ckan/templates`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.

.. note:: This is only for legacy code, and shouldn't be used anymore.

extra_public_paths
^^^^^^^^^^^^^^^^^^

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for static files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for additional files, before reverting to the ``ckan/public`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.

.. note:: This is only for legacy code, and shouldn't be used anymore.


Form Settings
-------------

.. _config-package-urls:

package_new_return_url & package_edit_return_url
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 package_new_return_url = http://datadotgc.ca/new_dataset_complete?name=<NAME>
 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

If integrating the Edit Dataset and New Dataset forms into a third-party interface, setting these options allows you to set the return address. When the user has completed the form and presses 'commit', the user is redirected to the URL specified.

The ``<NAME>`` string is replaced with the name of the dataset edited. Full details of this process are given in :doc:`form-integration`.

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


Search Settings
---------------

.. _ckan-site-id:

ckan.site_id
^^^^^^^^^^^^

Example::

 ckan.site_id = my_ckan_instance

CKAN uses Solr to index and search packages. The search index is linked to the value of the ``ckan.site_id``, so if you have more than one
CKAN instance using the same `solr_url`_, they will each have a separate search index as long as their ``ckan.site_id`` values are different. If you are only running
a single CKAN instance then this can be ignored.

Note, if you change this value, you need to rebuild the search index.

ckan.simple_search
^^^^^^^^^^^^^^^^^^

Example::

 ckan.simple_search = true

Default value:  ``false``

Switching this on tells CKAN search functionality to just query the database, (rather than using Solr). In this setup, search is crude and limited, e.g. no full-text search, no faceting, etc. However, this might be very useful for getting up and running quickly with CKAN.

.. _solr-url:

solr_url
^^^^^^^^

Example::

 solr_url = http://solr.okfn.org:8983/solr/ckan-schema-2.0

Default value:  ``http://solr.okfn.org:8983/solr``

This configures the Solr server used for search. The Solr schema found at that URL must be one of the ones in ``ckan/config/solr`` (generally the most recent one). A check of the schema version number occurs when CKAN starts.

Optionally, ``solr_user`` and ``solr_password`` can also be configured to specify HTTP Basic authentication details for all Solr requests.

.. note::  If you change this value, you need to rebuild the search index.

ckan.search.automatic_indexing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.automatic_indexing = 1

Make all changes immediately available via the search after editing or
creating a dataset. Default is true. If for some reason you need the indexing
to occur asynchronously, set this option to 0.

.. note:: This is equivalent to explicitly load the ``synchronous_search`` plugin.

ckan.search.solr_commit
^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.solr_commit = false

Default value:  ``true``

Make ckan commit changes solr after every dataset update change. Turn this to false if on solr 4.0 and you have automatic (soft)commits enabled to improve dataset update/create speed (however there may be a slight delay before dataset gets seen in results).

ckan.search.show_all_types
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.search.show_all_types = true

Default value:  ``false``

Controls whether the default search page (``/dataset``) should show only
standard datasets or also custom dataset types.

search.facet.limits
^^^^^^^^^^^^^^^^^^^

Example::

 search.facet.limits = 100

Default value:  ``50``

Sets the default number of searched facets returned in a query.

ckan.extra_resource_fields
^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.extra_resource_fields = alt_url

Default value: ``None``

List of the extra resource fields that would be used when searching.


Site Settings
-------------

.. _ckan-site-url:

ckan.site_url
^^^^^^^^^^^^^

Example::

  ckan.site_url = http://scotdata.ckan.net

Default value:  (none)

The primary URL used by this site. Used in the API to provide datasets with links to themselves in the web UI.

.. warning::

  This setting should not have a trailing / on the end.

ckan.api_url
^^^^^^^^^^^^

Example::

 ckan.api_url = http://scotdata.ckan.net/api

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

ckan.cache_expires
^^^^^^^^^^^^^^^^^^

Example::

  ckan.cache_expires = 2592000

Default value: ''

This sets ``Cache-Control`` header's max-age value.

ckan.page_cache_enable
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.page_cache_enable = True

Default value: ''

This enables the page caching.

moderated
^^^^^^^^^

Example::

  moderated = True

Default value: (none)

This controls if new datasets will require moderation approval before going public.

.. _ckan-tracking-enabled:

ckan.tracking_enabled
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.tracking_enabled = True

Default value: ``False``

This controls if CKAN will track the site usage. For more info, read :ref:`tracking`.


.. _email-settings:

E-mail Settings
---------------

smtp.server
^^^^^^^^^^^

Example::

  smtp.server = smtp.gmail.com:587

Default value: ``None``

The SMTP server to connect to when sending emails with optional port.

smtp.starttls
^^^^^^^^^^^^^

Example::

  smtp.starttls = True

Default value: ``None``

Whether or not to use STARTTLS when connecting to the SMTP server.

smtp.user
^^^^^^^^^

Example::

  smtp.user = your_username@gmail.com

Default value: ``None``

The username used to authenticate with the SMTP server.

smtp.password
^^^^^^^^^^^^^

Example::

  smtp.password = yourpass

Default value: ``None``

The password used to authenticate with the SMTP server.

.. _smtp-mail-from:

smtp.mail_from
^^^^^^^^^^^^^^

Example::

  smtp.mail_from = you@yourdomain.com

Default value: ``None``

The email address that emails sent by CKAN will come from. Note that, if left blank, the
SMTP server may insert its own.

email_to
^^^^^^^^

Example::

  email_to = you@yourdomain.com

Default value: ``None``

This controls where the error messages will be sent to.

error_email_from
^^^^^^^^^^^^^^^^

Example::

  error_email_from = paste@localhost

Default value: ``None``

This controls from which email the error messages will come from.


Authorization Settings
----------------------

debug
^^^^^

Example::

  debug = False

Default value: ``False``

This enables Pylons' interactive debugging tool, makes Fanstatic serve unminified JS and CSS
files, and enables CKAN templates' debugging features.

.. warning:: THIS SETTING MUST BE SET TO FALSE ON A PRODUCTION ENVIRONMENT.
             Debug mode will enable the interactive debugging tool, allowing ANYONE to
             execute malicious code after an exception is raised.

ckan.debug_supress_header
^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.debug_supress_header = False

Default value: ``False``

This configs if the debug information showing the controller and action
receiving the request being is shown in the header.

.. note:: This info only shows if debug is set to True.


Plugin Settings
---------------

ckan.plugins
^^^^^^^^^^^^

Example::

  ckan.plugins = disqus datapreview googleanalytics follower

Specify which CKAN extensions are to be enabled.

.. warning::  If you specify an extension but have not installed the code,  CKAN will not start.

Format as a space-separated list of the extension names. The extension name is the key in the [ckan.plugins] section of the extension's ``setup.py``. For more information on extensions, see :doc:`extensions`.

ckan.datastore.enabled
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datastore.enabled = True

Default value: ``False``

Controls if the Data API link will appear in Dataset's Resource page.

.. note:: This setting only applies to the legacy templates.

ckanext.stats.cache_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckanext.stats.cache_enabled = True

Default value:  ``True``

This controls if we'll use the 1 day cache for stats.


search.facets.default
^^^^^^^^^^^^^^^^^^^^^

Example::

  search.facets.default = 10

Default number of facets shown in search results.  Default 10.

search.facets.limit
^^^^^^^^^^^^^^^^^^^

Example::

  search.facets.limit = 50

Highest number of facets shown in search results.  Default 50.
