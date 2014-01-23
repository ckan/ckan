===================
Config File Options
===================

You can set many important options in the CKAN config file. By default, the
configuration file is located at ``/etc/ckan/development.ini`` or
``/etc/ckan/production.ini``. This section documents all of the config file
settings, for reference.

.. todo::

   Insert cross-ref to section about location of config file?

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
        ckan.plugins = stats text_preview recline_preview

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

This enables Pylons' interactive debugging tool, makes Fanstatic serve unminified JS and CSS
files, and enables CKAN templates' debugging features.

.. warning:: This option should be set to ``False`` for a public site.
   With debug mode enabled, a visitor to your site could execute malicious
   commands.


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


Site Settings
-------------

.. _ckan.site_url:

ckan.site_url
^^^^^^^^^^^^^

Example::

  ckan.site_url = http://scotdata.ckan.net

Default value:  (none)

The URL of your CKAN site. Many CKAN features that need an absolute URL to your
site use this setting.

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

.. _ckan.page_cache_enabled:

ckan.page_cache_enabled
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.page_cache_enabled = True

Default value: ``False``

This enables CKAN's built-in page caching.

.. warning::

   Page caching is an experimental feature.

.. _ckan.cache_enabled:

ckan.cache_enabled
^^^^^^^^^^^^^^^^^^

Example::

  ckan.cache_enabled = True

Default value: ``None``

Controls if we're caching CKAN's static files, if it's serving them.

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

 ckan.auth.user_create_groups = False

Default value: ``True``


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


Allow new user accounts to be created via the API.

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


Makes role permissions apply to all the groups down the hierarchy from the groups that the role is applied to.

e.g. a particular user has the 'admin' role for group 'Department of Health'. If you set the value of this option to 'admin' then the user will automatically have the same admin permissions for the child groups of 'Department of Health' such as 'Cancer Research' (and its children too and so on).

.. end_config-authorization


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

.. _ckan.simple_search:

ckan.simple_search
^^^^^^^^^^^^^^^^^^

Example::

 ckan.simple_search = true

Default value:  ``false``

Switching this on tells CKAN search functionality to just query the database, (rather than using Solr). In this setup, search is crude and limited, e.g. no full-text search, no faceting, etc. However, this might be very useful for getting up and running quickly with CKAN.

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

 ckan.search.show_all_types = true

Default value:  ``false``

Controls whether the default search page (``/dataset``) should show only
standard datasets or also custom dataset types.

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


Plugins Settings
----------------

.. _ckan.plugins:

ckan.plugins
^^^^^^^^^^^^

Example::

  ckan.plugins = disqus datapreview googleanalytics follower

Default value: ``stats text_preview recline_preview``

Specify which CKAN plugins are to be enabled.

.. warning::  If you specify a plugin but have not installed the code,  CKAN will not start.

Format as a space-separated list of the plugin names. The plugin name is the key in the ``[ckan.plugins]`` section of the extension's ``setup.py``. For more information on plugins and extensions, see :doc:`extensions/index`.

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

.. _ckan.datastore.enabled:

ckan.datastore.enabled
^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datastore.enabled = True

Default value: ``False``

Controls if the Data API link will appear in Dataset's Resource page.

.. note:: This setting only applies to the legacy templates.

.. _ckanext.stats.cache_enabled:

ckanext.stats.cache_enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckanext.stats.cache_enabled = True

Default value:  ``True``

This controls if we'll use the 1 day cache for stats.


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
          For this reason, it's better to overload the snippet in ``home/snippets/about_text.html``. For more information, see :doc:`theming`.

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

.. note:: This is only for legacy code, and shouldn't be used anymore.

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

.. _ckan.dataset.show_apps_ideas:

ckan.dataset.show_apps_ideas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ckan.dataset.show_apps_ideas::

 ckan.dataset.show_apps_ideas = false

Default value:  true

When set to false, or no, this setting will hide the 'Apps, Ideas, etc' tab on the package read page. If the value is not set, or is set to true or yes, then the tab will shown.

.. note::  This only applies to the legacy Genshi-based templates

.. _ckan.preview.direct:

ckan.preview.direct
^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.direct = png jpg jpeg gif

Default value: ``png jpg jpeg gif``

Defines the resource formats which should be embedded directly in an ``img`` tag
when previewing them.

.. _ckan.preview.loadable:

ckan.preview.loadable
^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.preview.loadable = html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom rss txt

Default value: ``html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom rss txt``

Defines the resource formats which should be loaded directly in an ``iframe``
tag when previewing them if no :doc:`data-viewer` can preview it.

.. _ckan.dumps_url:

ckan.dumps_url
^^^^^^^^^^^^^^

If there is a page which allows you to download a dump of the entire catalogue
then specify the URL here, so that it can be advertised in the
web interface. For example::

  ckan.dumps_url = http://ckan.net/dump/

For more information on using dumpfiles, see :ref:`paster db`.

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

The public key for your Recaptcha account, for example::

 ckan.recaptcha.publickey = 6Lc...-KLc

To get a Recaptcha account, sign up at: http://www.google.com/recaptcha

.. _ckan.recaptcha.privatekey:

ckan.recaptcha.privatekey
^^^^^^^^^^^^^^^^^^^^^^^^^

The private key for your Recaptcha account, for example::

 ckan.recaptcha.privatekey = 6Lc...-jP

Setting both :ref:`ckan.recaptcha.publickey` and
:ref:`ckan.recaptcha.privatekey` adds captcha to the user registration form.
This has been effective at preventing bots registering users and creating spam
packages.

.. _ckan.featured_groups:

ckan.featured_groups
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.featured_groups = group_one group_two

Default Value: (empty)

Defines a list of group names or group ids. This setting is used to display
groups and datasets from each group on the home page in the default templates
(2 groups and 2 datasets for each group are displayed).

.. _ckan.featured_organizations:

ckan.featured_orgs
^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.featured_orgs = org_one org_two

Default Value: (empty)

Defines a list of organization names or ids. This setting is used to display
organization and datasets from each group on the home page in the default
templates (2 groups and 2 datasets for each group are displayed).

.. _ckan.gravatar_default:

ckan.gravatar_default
^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.gravatar_default = monsterid

Default value: ``identicon``

This controls the default gravatar avatar, in case the user has none.

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

.. _ckan.template_title_deliminater:

ckan.template_title_deliminater
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

 ckan.template_title_deliminater = |

Default value:  ``-``

This sets the delimiter between the site's subtitle (if there's one) and its title, in HTML's ``<title>``.

.. _extra_template_paths:

extra_template_paths
^^^^^^^^^^^^^^^^^^^^

Example::

 extra_template_paths = /home/okfn/brazil_ckan_config/templates

To customise the display of CKAN you can supply replacements for the Genshi template files. Use this option to specify where CKAN should look for additional templates, before reverting to the ``ckan/templates`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.

.. _extra_public_paths:

extra_public_paths
^^^^^^^^^^^^^^^^^^

Example::

 extra_public_paths = /home/okfn/brazil_ckan_config/public

To customise the display of CKAN you can supply replacements for static files such as HTML, CSS, script and PNG files. Use this option to specify where CKAN should look for additional files, before reverting to the ``ckan/public`` folder. You can supply more than one folder, separating the paths with a comma (,).

For more information on theming, see :doc:`theming`.

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

.. _ofs.impl:

ofs.impl
^^^^^^^^

Example::

  ofs.impl = pairtree

Default value:  ``None``

Defines the storage backend used by CKAN: ``pairtree`` for local storage, ``s3`` for Amazon S3 Cloud Storage or ``google`` for Google Cloud Storage. Note that each of these must be accompanied by the relevant settings for each backend described below.

Deprecated, only available option is now pairtree.  This must be used nonetheless if upgrading for CKAN 2.1 in order to keep access to your old pairtree files.


.. _ofs.storage_dir:

ofs.storage_dir
^^^^^^^^^^^^^^^

Example::

  ofs.storage_dir = /data/uploads/

Default value:  ``None``

Only used with the local storage backend. Use this to specify where uploaded files should be stored, and also to turn on the handling of file storage. The folder should exist, and will automatically be turned into a valid pairtree repository if it is not already.

Deprecated, please use ckan.storage_path.  This must be used nonetheless if upgrading for CKAN 2.1 in order to keep access to your old pairtree files.




DataPusher Settings
-------------------

.. _ckan.datapusher.formats:

ckan.datapusher.formats
^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.formats = csv xls

Default value: ``csv xls application/csv application/vnd.ms-excel``

File formats that will be pushed to the DataStore by the DataPusher. When
adding or editing a resource which links to a file in one of these formats,
the DataPusher will automatically try to import its contents to the DataStore.


.. _ckan.datapusher.url:

ckan.datapusher.url
^^^^^^^^^^^^^^^^^^^

Example::

  ckan.datapusher.url = http://127.0.0.1:8800/

DataPusher endpoint to use when enabling the ``datapusher`` extension. If you
installed CKAN via :doc:`install-from-package`, the DataPusher was installed for you
running on port 8800. If you want to manually install the DataPusher, follow
the installation `instructions <http://docs.ckan.org/projects/datapusher>`_.


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

Default value: ``infinite``

This controls the number of activities to show in the Activity Stream. By default, it shows everything.


.. _ckan.email_notifications_since:

ckan.email_notifications_since
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example::

  ckan.email_notifications_since = 2 days

Default value: ``infinite``

Email notifications for events older than this time delta will not be sent.
Accepted formats: '2 days', '14 days', '4:35:00' (hours, minutes, seconds), '7 days, 3:23:34', etc.


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

Use this to specify the locale (language of the text) displayed in the CKAN Web UI. This requires a suitable `mo` file installed for the locale in the ckan/i18n. For more information on internationalization, see :doc:`i18n`. If you don't specify a default locale, then it will default to the first locale offered, which is by default English (alter that with `ckan.locales_offered` and `ckan.locales_filtered_out`.

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

.. _ckan.root_path:

ckan.root_path
^^^^^^^^^^^^^^

Example::

  ckan.root_path = /my/custom/path/{{LANG}}/foo

Default value: (none)

By default, the URLs are formatted as ``/some/url``, when using the default
locale, or ``/de/some/url`` when using the "de" locale, for example. This
lets you change this. You can use any path that you want, adding ``{{LANG}}``
where you want the locale code to go.







Form Settings
-------------

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

  smtp.server = smtp.gmail.com:587

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

  smtp.user = your_username@gmail.com

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

  smtp.mail_from = you@yourdomain.com

Default value: ``None``

The email address that emails sent by CKAN will come from. Note that, if left blank, the
SMTP server may insert its own.

.. _email_to:

email_to
^^^^^^^^

Example::

  email_to = you@yourdomain.com

Default value: ``None``

This controls where the error messages will be sent to.

.. _error_email_from:

error_email_from
^^^^^^^^^^^^^^^^

Example::

  error_email_from = paste@localhost

Default value: ``None``

This controls from which email the error messages will come from.
