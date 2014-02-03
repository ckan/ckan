.. This tocdepth stops Sphinx from putting every subsection title in this file
   into the master table of contents.

:tocdepth: 1

---------
Changelog
---------

v2.2 2014-02-04
===============

Note: This version does not require a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version requires a Solr schema upgrade (The Solr schema file has
been renamed, the schema file from the previous release is compatible
with this version, but users are encouraged to point to the new one,
see "API changes and deprecations")


Major:
 * Brand new automatic importer of tabular data to the DataStore, the
   DataPusher. This is much more robust and simple to deploy and maintain than
   its predecesor (ckanext-datastorer). Whole new UI for re-importing data to
   the DataStore and view the import logs (#932, #938, #940, #981, #1196, #1200
   ...)
 * Completely revamped file uploads that allow closer integration with resources
   and the DataStore, as well as making easir to integrate file uploads in other
   features. For example users can now upload images for organizations and
   groups. See "API changes and deprecations" if you are using the current
   FileStore. (#1273, #1173 ... )
 * UI and API endpoints for resource reordering (#1277)
 * Backend support for organization hierarchy, allowing parent and children
   organizations. Frontend needs to be implemented in extensions (#1038)
 * User invitations: it is now possible to create new users with just their
   email address. An invite email is sent to them, allowing to change their user
   name and password (#1178)
 * Disable user registration with a configuration option (#1226)
 * Great effort in improving documentation, specially for customizing CKAN, with
   a complete tutorial for writing extensions and customizing the theme. User
   and sysadmin guides have also been moved to the main documentation
   (#943, #847, #1253)

Minor:
 * Homepage modules to allow predefined layouts (#1126)
 * Ability to delete users (#1163)
 * Dedicated dataset groups page for displaying and managing them (#1102)
 * Implement organization_purge and group_purge action functions (#707)
 * Improve package_show performance (#1078)
 * Support internationalization of rendered dates and times (#1041)
 * Improve plugin load handling (#549)
 * Authorization function auditing for action functions (#1060)
 * Improve datetime rendering (#518)
 * New SQL indexes to improve performance (#1164)
 * Changes in requirements management (#1149)
 * Add offset/limit to package_list action (#1179)
 * Document all available configuraton options (#848)
 * Make CKAN sqlalchemy 0.8.4 compatible (#1427)
 * UI labelling and cleanup (#1030)
 * Better UX for empty groups/orgs (#1094)
 * Improve performance of group_dictize when the group has a lot of packages
   (#1208)
 * Hide __extras from extras on package_show (#1218)
 * "Clear all" link within each facet block is unnecessary  (#1263)
 * Term translations of organizations (#1274)
 * '--reset-db' option for when running tests (#1304)

Bug fixes:
 * Fix plugins load/unload issues (#547)
 * Improve performance when new_activities not needed (#1013)
 * Resource preview breaks when CSV headers include percent sign (#1067)
 * Package index not rebuilt when resources deleted (#1081)
 * Don't accept invalid URLs in resource proxy (#1106)
 * UI language reset after account creation (#1429)
 * Catch non-integer facet limits (#1118)
 * Error when deleting custom tags (#1114)
 * Organization images do not display on Organization user dashboard page
   (#1127)
 * Can not reactivate a deleted dataset from the UI (#607)
 * Non-existent user profile should give error (#1068)
 * Recaptcha not working in CKAN 2.0 (jinja templates) (#1070)
 * Groups and organizations can be visited with interchangeable URLs (#1180)
 * Dataset Source (url) and Version fields missing (#1187)
 * Fix problems with private / public datasets and organizations (#1188)
 * group_show should never return private data (#1191)
 * When editing a dataset, the organization field is not set (#1199)
 * Fix resource_delete action (#1216)
 * Fix trash purge action redirect broken for CKAN instances not at / (#1217)
 * Title edit for existing dataset changes the URL (#1232)
 * 'facet.limit' in package_search wrongly handled (#1237)
 * h.SI_number_span doesn't close <span /> correctly (#1238)
 * CkanVersionException wrongly raised (#1241)
 * (group|organization)_member_create only accepts username (and not id) (#1243)
 * package_create uses the wrong parameter for organization (#1257)
 * ValueError for non-int limit and offset query params (#1258)
 * Visibility field value not kept if there are errors on the form (#1265)
 * package_list should not return private datasets (#1295)
 * Fix 404 on organization activity stream and about page (#1298)
 * Fix placeholder images broken on non-root locations (#1309)
 * "Add Dataset" button shown on org pages when not authorized (#1348)
 * Fix exception when visiting organization history page (#1359)
 * Fix search ordering on organization home page (#1368)
 * datastore_search_sql failing for some anonymous users (#1373)
 * related_list logic function throws a 503 without any parameters (#1384)
 * Disabling activity_streams borks editing groups and user (#1421)
 * Member Editing Fixes (#1454)
 * Bulk editing broken in IE7 (#1455)
 * Fix group deletion in IE7 (#1460)
 * And many, many more!

API changes and deprecations:
 * The Solr schema file is now always named ``schema.xml`` regardless of the
   CKAN version. Old schema files have been kept for backwards compatibility
   but users are encouraged to point to the new unified one (#1314)
 * The FileStore and file uploads have been completely refactored and simplified
   to only support local storage backend. The links from previous versions of
   the FileStore to hosted files will still work, but there is a command
   available to migrate the files to new Filestore. See this page for more
   details:
   http://docs.ckan.org/en/latest/filestore.html#filestore-21-to-22-migration
 * By default, the authorization for any action defined from an extension will
   require a logged in user, otherwise a :py:class:`ckan.logic.NotAuthorized`
   exception will be raised. If an action function allows anonymous access (eg
   search, show status, etc) the ``auth_allow_anonymous_access`` decorator
   (available on the plugins toolkit) must be used (#1210)
 * ``package_search`` now returns results with custom schemas applied like
   ``package_show``, a ``use_default_schema`` parameter was added to request the
   old behaviour, this change may affect customized search result templates
   (#1255)
 * The ``ckan.api_url`` configuration option has been completely removed and it
   can no longer be used (#960)
 * The ``edit`` and ``after_update`` methods of IPackageController plugins are now
   called when updating a resource using the web frontend or the
   resource_update API action (#1052)
 * Dataset moderation has been deprecated, and the code will probably be removed
   in later CKAN versions (#1139)
 * Some front end libraries have been updated, this may affect existing custom
   themes: Bootstrap 2.0.3 > 2.3.2, Font Awesome 3.0.2 > 3.2.1,
   jQuery 1.7.2 > 1.10.2 (#1082)
 * SQLite is officially no longer supported as the tests backend

Troubleshooting:
 * Exception on startup after upgrading from a previous CKAN version::

     AttributeError: 'instancemethod' object has no attribute 'auth_audit_exempt'

   Make sure that you are not loading a 2.1-only plugin (eg ``datapusher-ext``)
   and update all the plugin in your configuration file to the latest stable
   version.

 * Exception on startup after upgrading from a previous CKAN version::

     File "/usr/lib/ckan/default/src/ckan/ckan/lib/dictization/model_dictize.py", line 330, in package_dictize
         result_dict['metadata_modified'] = pkg.metadata_modified.isoformat()
     AttributeError: 'NoneType' object has no attribute 'isoformat'

   One of the database changes on this version is the addition of a
   ``metadata_modified`` field in the package table, that was filled during the
   DB migration process. If you have previously migrated the database and revert
   to an older CKAN version the migration process may have failed at this step,
   leaving the fields empty. Also make sure to restart running processes like
   harvesters after the update to make sure they use the new code base.

v2.1.2 2014-02-04
=================

Bug fixes:
 * Fix context for group/about setup_template_variables (#1433)
 * Call setup_template_variables in group/org read, about and bulk_process (#1281)
 * Remove repeated sort code in package_search (#1461)
 * Ensure that check_access is called on activity_create (#1421)
 * Fix visibility validator (#1188)
 * Remove p.toolkit.auth_allow_anonymous_access as it is not available on 2.1.x (#1373)
 * Add organization_revision_list to avoid exception on org history page (#1359)
 * Fix activity and about organization pages (#1298)
 * Show 404 instead of login page on user not found (#1068)
 * Don't show Add Dataset button on org pages unless authorized (#1348)
 * Fix datastore_search_sql authorization function (#1373)
 * Fix extras deletion (#1449)
 * Better word breaking on long words (#1398)
 * Fix activity and about organization pages (#1298)
 * Remove limit of number of arguments passed to ``user add`` command.
 * Fix related_list logic function (#1384)
 * Avoid UnicodeEncodeError on feeds when params contains non ascii characters

v2.1.1 2013-11-8
================

Bug fixes:
 * Fix errors on preview on non-root locations (#960)
 * Fix place-holder images on non-root locations (#1309)
 * Don't accept invalid URLs in resource proxy (#1106)
 * Make sure came_from url is local (#1039)
 * Fix logout redirect in non-root locations (#1025)
 * Wrong auth checks for sysadmins on package_create (#1184)
 * Don't return private datasets on package_list (#1295)
 * Stop tracking failing when no lang/encoding headers (#1192)
 * Fix for paster db clean command getting frozen
 * Fix organization not set when editing a dataset (#1199)
 * Fix PDF previews (#1194)
 * Fix preview failing on private datastore resources (#1221)

v2.1 2013-08-13
===============

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version does not require a Solr schema upgrade

.. note:: The ``json_preview`` plugin has been renamed to ``text_preview``
 (see #266). If you are upgrading CKAN from a previous version you need
 to change the plugin name on your CKAN config file after upgrading to avoid
 a PluginNotFound exception.


Major:
 * Bulk updates of datasets within organizations (delete, make public/private) (#278)
 * Organizations and Groups search (#303)
 * Generic text preview extension for JSON, XML and plain text files (#226)
 * Improve consistency of the Action API (#473)
 * IAuthenticator interface for plugging into authorization platforms (Work
   in progress) (#1007)
 * New clearer dashboard with more information easier to access (#626)
 * New ``rebuild_fast`` command to speed up reindex using multiple cores (#700)
 * Complete restructure of the documentation, with updated sections on
   installation, upgrading, release process, etc and guidelines on how to write
   new documentation (#769 and multiple others)

Minor:
 * Add group members page to templates (#844)
 * Show search facets on organization page (#776)
 * Changed default sort ordering (#869)
 * More consistent display of buttons across pages (#890)
 * History page ported to new templates (#368)
 * More blocks to templates to allow furhter customization (#688)
 * Improve imports from lib.helpers (#262)
 * Add support for callback parameter on Action API (#414)
 * Create site_user at startup (#952)
 * Add warning before deleting an organization (#803)
 * Remove flags from language selector (#822)
 * Hide the Data API button when datastore is disabled (#752)
 * Pin all requirements and separate minimal requirements in a separate file (#491, #1149)
 * Better preview plugin selection (#1002)
 * Add new functions to the plugins toolkit (#1015)
 * Improve ExampleIDatasetFormPlugin (#2750)
 * Extend h.sorted_extras() to do substitutions and auto clean keys (#440)
 * Separate default database for development and testing (#517)
 * More descriptive Solr exceptions when indexing (#674)
 * Validate datastore input through schemas (#905)

Bug fixes:
 * Fix 500 on password reset (#264)
 * Fix exception when indexing a wrong date on a _date field (#267)
 * Fix datastore permissions issues (#652)
 * Placeholder images are not linked with h.url_for_static (#948)
 * Explore dropdown menu is hidden behind other resources in IE (#915)
 * Buttons interrupt file uploading (#902)
 * Fix resource proxy encoding errors (#896)
 * Enable streaming in resource proxy (#989)
 * Fix cache_dir and beaker paths on deployment.ini_tmpl (#888)
 * Fix multiple issues on create dataset form on IE (#881)
 * Fix internal server error when adding member (#869)
 * Fix license faceting (#853)
 * Fix exception in dashboard (#830)
 * Fix Google Analytics integration (#827)
 * Fix ValueError when resource size is not an integer (#1009)
 * Catch NotFound on new resource when package does not exist (#1010)
 * Fix Celery configuration to allow overriding from config (#1027)
 * came_from after login is validated to not redidirect to another site (#1039)
 * And many, many more!

Deprecated and removed:
 * The ``json_preview`` plugin has been replaced by a new ``text_preview``
   one. Please update your config files if using it. (#226)

Known issues:
 * Under certain authorization setups the frontend for the groups functionality
   may not work as expected (See #1176 #1175).

v2.0.4 2014-02-04
=================

Bug fixes:
 * Fix extras deletion (#1449)
 * Better word breaking on long words (#1398)
 * Fix activity and about organization pages (#1298)
 * Show 404 instead of login page on user not found (#1068)
 * Remove limit of number of arguments passed to ``user add`` command.
 * Fix related_list logic function (#1384)

v2.0.3 2013-11-8
================

Bug fixes:
 * Fix errors on preview on non-root locations (#960)
 * Don't accept invalid URLs in resource proxy (#1106)
 * Make sure came_from url is local (#1039)
 * Fix logout redirect in non-root locations (#1025)
 * Don't return private datasets on package_list (#1295)
 * Stop tracking failing when no lang/encoding headers (#1192)
 * Fix for paster db clean command getting frozen


v2.0.2 2013-08-13
=================

Bug fixes:
 * Fix markdown in group descriptions (#303)
 * Fix resource proxy encoding errors (#896)
 * Fix datastore exception on first run (#907)
 * Enable streaming in resource proxy (#989)
 * Fix in user search (#1024)
 * Fix Celery configuration to allow overriding from config (#1027)
 * Undefined function on organizations controller (#1036)
 * Fix license not translated in orgs/groups (#1040)
 * Fix link to documentation from the footer (#1062)
 * Fix missing close breadcrumb tag in org templates (#1071)
 * Fix recently_changed_packages_activity_stream function (#1159)
 * Fix Recline map sidebar not showing in IE 7-8 (#1133)


v2.0.1 2013-06-11
=================

Bug fixes:
 * Use IDatasetForm schema for resource_update (#897)
 * Fixes for CKAN being run on a non-root URL (#948, #913)
 * Fix resource edit errors losing info (#580)
 * Fix Czech translation (#900)
 * Allow JSON filters for datastore_search on GET requests (#917)
 * Install vdm from the Python Package Index (#764)
 * Allow extra parameters on Solr queries (#739)
 * Create site user at startup if it does not exist (#952)
 * Fix modal popups positioning (#828)
 * Fix wrong redirect on dataset form on IE (#963)


v2.0 2013-05-10
===============

.. note:: Starting on v2.0, issue numbers with four digits refer to the old
 ticketing system at http://trac.ckan.org and the ones with three digits refer
 to GitHub issues. For example:

 * #3020 is http://trac.ckan.org/ticket/3020
 * #271 is https://github.com/ckan/ckan/issues/271

 Some GitHub issues URLs will redirect to GitHub pull request pages.

.. note:: v2.0 is a huge release so the changes listed here are just the
 highlights. Bug fixes are not listed.

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version requires a Solr schema upgrade

Organizations based authorization (see :doc:`authorization`):
 CKAN's new "organizations" feature replaces the old authorization system
 with a new one based on publisher organizations. It replaces the "Publisher
 Profile and Workflow" feature from CKAN 1.X, any instances relying on it will
 need to be updated.

 * New organization-based authorization and organization of datasets
 * Supports private datasets
 * Publisher workflow
 * New authorization ini file options


New frontend:
 CKAN's frontend has been completely redesigned, inside and out. There is
 a new default theme and the template engine has moved from Genshi to
 Jinja2. Any custom templates using Genshi will need to be updated, although
 there is a :ref:`ckan.legacy_templates` setting to aid in the migration.

 * Block-based template inheritance
 * Custom jinja tags: {% ckan_extends %}, {% snippet %} and {% url_for %} (#2502, #2503)
 * CSS "primer" page for theme developers
 * We're now using LESS for CSS
 * Scalable font icons (#2563)
 * Social sharing buttons (google plus, facebook, twitter)
   (this replaces the ckanext-social extension)
 * Three-stage dataset creation form (#2501)
 * New `paster front-end-build` command does everything needed to build the
   frontend for a production CKAN site (runs `paster less` to compile the css
   files, `paster minify` to minify the css and js files, etc.)

Plugins & Extensions:
 * New plugins toolkit provides a stable set of utility and helper functions
   for CKAN plugins to depend on.
 * The IDatasetForm plugin interface has been redesigned (note: this breaks
   backwards-compatibility with existing IDatasetForm plugins) (#649)
 * Many IDatasetForm bugs were fixed
 * New example extensions in core, and better documentation for the relevant
   plugin interfaces: example_itemplatehelpers (#447),
   example_idatasetform (#2750), hopefully more to come in 2.1!
 * New IFacets interface that allows to modify the facets shown on various
   pages. (#400)
 * The get_action() function now automatically adds 'model' and 'session' to
   the context dict (this saves on boiler-plate code, and means plugins don't
   have to import ckan.model in order to call get_action()) (#172)

Activity Streams, Following & User Dashboard:
 * New visual design for activity streams (#2941)
 * Group activity streams now include activities for changes to any of the
   group's datasets (#1664)
 * Group activity streams now appear on group pages (previously they could
   only be retrieved via the api)
 * Dataset activity streams now appear on dataset pages (previously they could
   only be retrieved via the api) (#3024)
 * Users can now follow groups (previously you could only follow users or
   datasets) (#3005)
 * Activity streams and following are also supported for organizations (#505)
 * When you're logged into CKAN, you now get a notifications count in the
   top-right corner of the site, telling you how many new notifications you
   have on your dashboard. Clicking on the count takes you to your dashboard
   page to view your notifications. (#3009)
 * Optionally, you can also receive notifications by email when you have new
   activities on your dashboard (#1635)
 * Infinite scrolling of activity streams (if you scroll to the bottom of a
   an activity stream, CKAN will automatically load more activities) (#3018)
 * Redesigned user dashboard (#3028):

   - New dropdown-menu enables you to filter you dashboard activity stream to
     show only activities from a particular user, dataset, group or
     organization that you're following
   - New sidebar shows previews and unfollow buttons (when the activity stream
     is filtered)
 * New :ref:`ckan.activity_streams_enabled` config file setting allows you to
   disable the generation of activity streams (#654)

Data Preview:
 * PDF files preview (#2203)
 * JSON files preview
 * HTML pages preview (in an iframe) (#2888)
 * New plugin extension point that allows plugins to add custom data previews
   for different data types (#2961)
 * Improved Recline Data Explorer previews (CSV files, Excel files..)
 * Plain text files preview


API:
 * The Action API is now CKAN's default API, and the API documentation has
   been rewritten (#357)

Other highlights:
 * CKAN now has continuous integration testing at
   https://travis-ci.org/okfn/ckan/
 * Dataset pages now have <link rel="alternate" type="application/rdf+xml"
   links in the HTML headers, allows linked-data tools to find CKAN's RDF
   rendering of a dataset's metadata (#413)
 * CKAN's DataStore and Data API have been rewritten, and now use PostgreSQL
   instead of elasticsearch, so there's no need to install elasticsearch
   anymore (this feature was also back-ported to CKAN 1.8) (#2733)
 * New Config page for sysadmins (/ckan-admin/config) enables sysadmins to set
   the site title, tag line, logo, the intro text shown on the front page,
   the about text shown on the /about page, select a theme, and add custom
   CSS (#2302, #2781)
 * New `paster color` command for creating color schemes
 * Fanstatic integration (#2371):

   - CKAN now uses Fanstatic to specify required static resource files
     (js, css..) for web pages
   - Enables each page to only include the static files that it needs,
     reducing page loads
   - Enables CKAN to use bundled and minified static files, further reducing
     page loads
   - CKAN's new `paster minify` command is used to create minified js and
     css files (#2950) (also see `paster front-end-build`)
 * CKAN will now recognise common file format strings such as
   "application/json", "JSON", ".json" and "json" as a single file type "json"
   (#2416)
 * CKAN now supports internalization of strings in javascript files, the new
   `paster trans` command is used to pull translatable strings out of
   javascript files (#2774, #2750)
 * convert_to/from_extras have been fixed to not add quotes around strings (#2930)
 * Updated CKAN coding standards (#3020) and CONTRIBUTING.rst file
 * Built-in page view counting and 'popular' badges on datasets and resources
   There's also a paster command to export the tracking data to a csv file (#195)
 * Updated CKAN Coding Standards and new CONTRIBUTING.rst file
 * You can now change the sort ordering of datasets on the dataset search page

Deprecated and removed:
 * The IGenshiStreamFilter plugin interface is deprecated (#271), use the
   ITemplateHelpers plugin interface instead
 * The Model, Search and Util APIs are deprecated, use the Action API instead
 * Removed restrict_template_vars config setting (#2257)
 * Removed deprecated facet_title() template helper function, use
   get_facet_title() instead (#2257)
 * Removed deprecated am_authorized() template helper function, use
   check_access() instead (#2257)
 * Removed deprecated datetime_to_datestr() template helper function (#2257)


v1.8.2 2013-08-13
=================

Bug fixes:
 * Fix for using harvesters with organization setup
 * Refactor for user update logic
 * Tweak resources visibility query


v1.8.1 2013-05-10
=================

Bug fixes:
 * Fixed possible XSS vulnerability on html input (#703)
 * Fix unicode template 500 error (#808)
 * Fix error on related controller


v1.8 2012-10-19
===============

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version does not require a Solr schema upgrade

Major
 * New 'follow' feature that allows logged in users to follow other users or
   datasets (#2304)
 * New user dashboard that shows an activity stream of all the datasets and
   users you are following. Thanks to Sven R. Kunze for his work on this (#2305)
 * New version of the Datastore. It has been completely rewritten to use
   PostgreSQL as backend, it is more stable and fast and supports SQL queries
   (#2733)
 * Clean up and simplifyng of CKAN's dependencies and source install
   instructions. Ubuntu 12.04 is now supported for source installs (#2428,#2592)
 * Big speed improvements when indexing datasets (#2788)
 * New action API reference docs, which individually document each function and
   its arguments and return values (#2345)
 * Updated translations, added Japanese and Korean translations

Minor
 * Add source install upgrade docs (#2757)
 * Mark more strings for translation (#2770)
 * Allow sort ordering of dataset listings on group pages (#2842)
 * Reenable simple search option (#2844)
 * Editing organization removes all datasets (#2845)
 * Accessibility enhancements on templates

Bug fixes
 * Fix for relative url being used when doing file upload to local storage
 * Various fixes on IGroupFrom (#2750)
 * Fix group dataset sort (#2722)
 * Fix adding existing datasets to organizations (#2843)
 * Fix 500 error in related controller (#2856)
 * Fix for non-open licenses appearing open
 * Editing organization removes all datasets (#2845)

API changes and deprecation:
 * Template helper functions are now restricted by default. By default only
   those helper functions listed in lib.helpers.__allowed_functions__
   are available to templates. The full functions can still be made
   available by setting `ckan.restrict_template_vars = false` in your ini file.
   Only restricted functions will be allowed in future versions of CKAN.
 * Deprecated functions related to the old faceting data structure have
   been removed:  `helpers.py:facet_items()`, `facets.html:facet_sidebar()`,
   `facets.html:facet_list_items()`.
   Internal use of the old facets datastructure (attached to the context,
   `c.facets`) has been superseded by use of the improved facet data structure,
   `c.search_facets`.  The old data structure is still available on `c.facets`,
   but is deprecated, and will be removed in future versions. (#2313)


v1.7.4 2013-08-13
=================

Bug fixes:
 * Refactor for user update logic
 * Tweak resources visibility query


v1.7.3 2013-05-10
=================

Bug fixes:
 * Fixed possible XSS vulnerability on html input (#703)


v1.7.2 2012-10-19
=================

Minor:
 * Documentation enhancements regarding file uploads

Bug fixes:
 * Fixes for lincences i18n
 * Remove sensitive data from user dict (#2784)
 * Fix bug in feeds controller (#2869)
 * Show dataset author and maintainer names even if they have no emails
 * Fix URLs for some Amazon buckets
 * Other minor fixes


v1.7.1 2012-06-20
=================

Minor:
 * Documentation enhancements regarding install and extensions (#2505)
 * Home page and search results speed improvements (#2402,#2403)
 * I18n: Added Greek translation and updated other ones (#2506)

Bug fixes:
 * UI fixes (#2507)
 * Fixes for i18n login and logout issues (#2497)
 * Date on add/edit resource breaks if offset is specified (#2383)
 * Fix in organizations read page (#2509)
 * Add synchronous_search plugin to deployment.ini template (#2521)
 * Inconsistent language on license dropdown (#2575)
 * Fix bug in translating lists in multilingual plugin
 * Group autocomplete doesn't work with multiple words (#2373)
 * Other minor fixes


v1.7 2012-05-09
===============

Major:
 * Updated SOLR schema (#2327). Note: This will require and update of the SOLR schema file and a reindex.
 * Support for Organization based workflow, with membership determinig access permissions to datasets (#1669,#2255)
 * Related items such as visualizations, applications or ideas can now be added to datasets (#2204)
 * Restricted vocabularies for tags, allowing grouping related tags together (#1698)
 * Internal analytics that track number of views and downloads for datasets and resources (#2251)
 * Consolidated multilingual features in an included extension (#1821,#1820)
 * Atom feeds for publishers, tags and search results (#1593,#2277)
 * RDF dump paster command (#2303)
 * Better integration with the DataStore, based on ElasticSearch, with nice helper docs (#1797)
 * Updated the Recline data viewer with new features such as better graphs and a map view (#2236,#2283)
 * Improved and redesigned documentation (#2226,#2245,#2248)

Minor:
 * Groups can have an image associated (#2275)
 * Basic resource validation (#1711)
 * Ability to search without accents for accented words (#906)
 * Weight queries so that title is more important than rest of body (#1826)
 * Enhancements in the dataset and resource forms (#1506)
 * OpenID can now be disabled (#1830)
 * API and forms use same validation (#1792)
 * More robust bulk search indexing, with options to ignore exceptions and just refresh (#1616i,#2232)
 * Modify where the language code is placed in URLs (#2261)
 * Simplified licenses list (#1359)
 * Add extension point for dataset view (#1741)

Bug fixes:
 * Catch exceptions on the QA archiver (#1809)
 * Error when changing language when CKAN is mounted in URL (#1804)
 * Naming of a new package/group can clash with a route (#1742)
 * Can't delete all of a package's resources over REST API (#2266)
 * Group edit form didn't allow adding multiple datasets at once (#2292)
 * Fix layout bugs in IE 7 (#1788)
 * Bug with Portugese translation and Javascript (#2318)
 * Fix broken parse_rfc_2822 helper function (#2314)

v1.6 2012-02-24
===============

Major:
 * Resources now have their own pages, as well as showing in the Dataset (#1445, #1449)
 * Group pages enhanced, including in-group search (#1521)
 * User pages enhanced with lists of datasets (#1396) and recent activity (#1515)
 * Dataset view page decluttered (#1450)
 * Tags not restricted to just letters and dashes (#1453)
 * Stats Extension and Storage Extension moved into core CKAN (#1576, #1608)
 * Ability to mounting CKAN at a sub-URL (#1401, #1659)
 * 5 Stars of Openness ratings show by resources, if ckanext-qa is installed (#1583)
 * Recline Data Explorer (for previewing and plotting data) improved and v2 moved into core CKAN (#1602, #1630)

Minor:
 * 'About' page rewritten and easily customisable in the config (#1626)
 * Gravatar picture displayed next to My Account link (#1528)
 * 'Delete' button for datasets (#1425)
 * Relationships API more RESTful, validated and documented (#1695)
 * User name displayed when logged in (#1529)
 * Database dumps now exclude deleted packages (#1623)
 * Dataset/Tag name length now limited to 100 characters in API (#1473)
 * 'Status' API call now includes installed extensions (#1488)
 * Command-line interface for list/read/deleting datasets (#1499)
 * Slug API calls tidied up and documented (#1500)
 * Users nagged to add email address if missing from their account (#1413)
 * Model and API for Users to become Members of a Group in a certain Capacity (#1531, #1477)
 * Extension interface to adjust search queries, indexing and results (#1547, #1738)
 * API for changing permissions (#1688)

Bug fixes:
 * Group deletion didn't work (#1536)
 * metadata_created used to return an entirely wrong date (#1546)
 * Unicode characters in field-specific API search queries caused exception (since CKAN 1.5) (#1798)
 * Sometimes task_status errors weren't being recorded (#1483)
 * Registering or Logging in failed silently when already logged in (#1799)
 * Deleted packages were browseable by administrators and appeared in dumps (#1283, #1623)
 * Facicon was a broken link unless corrected in config file (#1627)
 * Dataset search showed last result of each page out of order (#1683)
 * 'Simple search' mode showed 0 packages on home page (#1709)
 * Occasionally, 'My Account' shows when user is not logged in (#1513)
 * Could not change language when on a tag page that had accented characters or dataset creation page (#1783, #1791)
 * Editing package via API deleted its relationships (#1786)


v1.5.1 2012-01-04
=================

Major:
 * Background tasks (#1363, #1371, #1408)
 * Fix for security issue affecting CKAN v1.5 (#1585)

Minor:
 * Language support now excellent for European languages: en de fr it es no sv pl ru pt cs sr ca
 * Web UI improvements:
    * Resource editing refreshed
    * Group editing refreshed
    * Indication that group creation requires logging-in (#1004)
    * Users' pictures displayed using Gravatar (#1409)
    * 'Welcome' banner shown to new users (#1378)
    * Group package list now ordered alphabetically (#1502)
 * Allow managing a dataset's groups also via package entity API (#1381)
 * Dataset listings in API standardised (#1490)
 * Search ordering by modification and creation date (#191)
 * Account creation disallowed with Open ID (create account in CKAN first) (#1386)
 * User name can be modified (#1386)
 * Email address required for registration (for password reset) (#1319)
 * Atom feeds hidden for now
 * New config options to ease CSS insertion into the template (#1380)
 * Removed ETag browser cache headers (#1422)
 * CKAN version number and admin contact in new 'status_show' API (#1087)
 * Upgrade SQLAlchemy to 0.7.3 (compatible with Postgres up to 9.1) (#1433)
 * SOLR schema is now versioned (#1498)

Bug fixes:
 * Group ordering on main page was alphabetical but should be by size (since 1.5) (#1487)
 * Package could get added multiple times to same Group, distorting Group size (#1484)
 * Search index corruption when multiple CKAN instances on a server all storing the same object (#1430)
 * Dataset property metadata_created had wrong value (since v1.3) (#1546)
 * Tag browsing showed tags for deleted datasets (#920)
 * User name change field validation error (#1470)
 * You couldn't edit a user with a unicode email address (#1479)
 * Package search API results missed the extra fields (#1455)
 * OpenID registration disablement explained better (#1532)
 * Data upload (with ckanext-storage) failed if spaces in the filename (#1518)
 * Resource download count fixed (integration with ckanext-googleanalytics) (#1451)
 * Multiple CKANs with same dataset IDs on the same SOLR core would conflict (#1462)


v1.5 2011-11-07
===============
**Deprecated due to security issue #1585**

Major:
 * New visual theme (#1108)
    * Package & Resource edit overhaul (#1294/#1348/#1351/#1368/#1296)
    * JS and CSS reorganization (#1282, #1349, #1380)
 * Apache Solr used for search in core instead of Postgres (#1275, #1361, #1365)
 * Authorization system now embedded in the logic layer (#1253)
 * Captcha added for user registration (#1307, #1431)
 * UI language translations refreshed (#1292, #1350, #1418)
 * Action API improved with docs now (#1315, #1302, #1371)

Minor:
 * Cross-Origin Resource Sharing (CORS) support (#1271)
 * Strings to translate into other languages tidied up (#1249)
 * Resource format autocomplete (#816)
 * Database disconnection gives better error message (#1290)
 * Log-in cookie is preserved between sessions (#78)
 * Extensions can access formalchemy forms (#1301)
 * 'Dataset' is the new name for 'Package' (#1293)
 * Resource standard fields added: type, format, size (#1324)
 * Listing users speeded up (#1268)
 * Basic data preview functionality moved to core from QA extension (#1357)
 * Admin Extension merged into core CKAN (#1264)
 * URLs in the Notes field are automatically linked (#1320)
 * Disallow OpenID for account creation (but can be linked to accounts) (#1386)
 * Tag name now validated for max length (#1418)

Bug fixes:
 * Purging of revisions didn't work (since 1.4.3) (#1258)
 * Search indexing wasn't working for SOLR (since 1.4.3) (#1256)
 * Configuration errors were being ignored (since always) (#1172)
 * Flash messages were temporarily held-back when using proxy cache (since 1.3.2) (#1321)
 * On login, user told 'welcome back' even if he's just registered (#1194)
 * Various minor exceptions cropped up (mostly since 1.4.3) (#1334, #1346)
 * Extra field couldn't be set to original value when key deleted (#1356)
 * JSONP callback parameter didn't work for the Action API (since 1.4.3) (#1437)
 * The same tag could be added to a package multiple times (#1331)


v1.4.3.1 2011-09-30
===================
Minor:
 * Added files to allow debian packaging of CKAN
 * Added Catalan translation

Bug fixes:
 * Incorrect Group creation form parameter caused exception (#1347)
 * Incorrect AuthGroup creation form parameter caused exception (#1346)


v1.4.3 2011-09-13
=================
Major:
  * Action API (API v3) (beta version) provides powerful RPC-style API to CKAN data (#1335)
  * Documentation overhaul (#1142, #1192)

Minor:
  * Viewing of a package at a given date (as well as revision) with improved UI (#1236)
  * Extensions can now add functions to the logic layer (#1211)
  * Refactor all remaining database code out of the controllers and into the logic layer (#1229)
  * Any OpenID log-in errors that occur are now displayed (#1228)
  * 'url' field added to search index (e9214)
  * Speed up tag reading (98d72)
  * Cope with new WebOb version 1 (#1267)
  * Avoid exceptions caused by bots hitting error page directly (#1176)
  * Too minor to mention: #1234,

Bug fixes:
  * Re-adding tags to a package failed (since 1.4.1 in Web UI, 1.4 in API) (#1239)
  * Modified revisions retrieved over API caused exception (since 1.4.2) (#1310)
  * Whichever language you changed to, it announced "Language set to: English" (since 1.3.1) (#1082)
  * Incompatibilities with Python 2.5 (since 1.3.4.1 and maybe earlier) (#1325)
  * You could create an authorization group without a name, causing exceptions displaying it (#1323)
  * Revision list wasn't showing deleted packages (b21f4)
  * User editing error conditions handled badly (#1265)


v1.4.2 2011-08-05
=================
Major:
  * Packages revisions can be marked as 'moderated' (#1141, #1147)
  * Password reset facility (#1186/#1198)

Minor:
  * Viewing of a package at any revision (#1236)
  * API POSTs can be of Content-Type "application/json" as alternative to existing "application/x-www-form-urlencoded" (#1206)
  * Caching of static files (#1223)

Bug fixes:
  * When you removed last row of resource table, you could't add it again - since 1.0 (#1215)
  * Adding a tag to package that had it previously didn't work - since 1.4.1 in UI and 1.4.0 in API (#1239)
  * Search index was not updated if you added a package to a group - since 1.1 (#1140)
  * Exception if you had any Groups and migrated between CKAN v1.0.2 to v1.2 (migration 29) - since v1.0.2 (#1205)
  * API Package edit requests returned the Package in a different format to usual - since 1.4 (#1214)
  * API error responses were not all JSON format and didn't have correct Content-Type (#1214)
  * API package delete doesn't require a Content-Length header (#1214)


v1.4.1 2011-06-27
=================
Major:
  * Refactor Web interface to use logic layer rather than model objects directly. Forms now defined in navl schema and designed in HTML template. Forms use of Formalchemy is deprecated. (#1078)

Minor:
  * Links in user-supplied text made less attractive to spammers (nofollow) #1181
  * Package change notifications - remove duplicates (#1149)
  * Metadata dump linked to (#1169)
  * Refactor authorization code to be common across Package, Group and Authorization Group (#1074)

Bug fixes
  * Duplicate authorization roles were difficult to delete (#1083)


v1.4 2011-05-19
===============
Major:
  * Authorization forms now in grid format (#1074)
  * Links to RDF, N3 and Turtle metadata formats provided by semantic.ckan.net (#1088)
  * Refactor internal logic to all use packages in one format - a dictionary (#1046)
  * A new button for administrators to change revisions to/from a deleted state (#1076)

Minor:
  * Etags caching can now be disabled in config (#840)
  * Command-line tool to check search index covers all packages (#1073)
  * Command-line tool to load/dump postgres database (#1067)

Bug fixes:
  * Visitor can't create packages on new CKAN install - since v1.3.3 (#1090)
  * OpenID user pages couldn't be accessed - since v1.3.2 (#1056)
  * Default site_url configured to ckan.net, so pages obtains CSS from ckan.net- since v1.3 (#1085)


v1.3.3 2011-04-08
=================
Major:
  * Authorization checks added to editing Groups and PackageRelationships (#1052)
  * API: Added package revision history (#1012, #1071)

Minor:
  * API can take auth credentials from cookie (#1001)
  * Theming: Ability to set custom favicon (#1051)
  * Importer code moved out into ckanext-importlib repo (#1042)
  * API: Group can be referred to by ID (in addition to name) (#1045)
  * Command line tool: rights listing can now be filtered (#1072)

Bug fixes:
  * SITE_READ role setting couldn't be overridden by sysadmins (#1044)
  * Default 'reader' role too permissive (#1066)
  * Resource ordering went wrong when editing and adding at same time (#1054)
  * GET followed by PUTting a package stored an incorrect license value (#662)
  * Sibling package relationships were shown for deleted packages (#664)
  * Tags were displayed when they only apply to deleted packages (#920)
  * API: 'Last modified' time was localised - now UTC (#1068)


v1.3.2 2011-03-15
=================
Major:
  * User list in the Web interface (#1010)
  * CKAN packaged as .deb for install on Ubuntu
  * Resources can have extra fields (although not in web interface yet) (#826)
  * CSW Harvesting - numerous of fixes & improvements. Ready for deployment. (#738 etc)
  * Language switcher (82002)

Minor:
  * Wordpress integration refactored as a Middleware plugin (#1013)
  * Unauthorized actions lead to a flash message (#366)
  * Resources Groups to group Resources in Packages (#956)
  * Plugin interface for authorization (#1011)
  * Database migrations tested better and corrected (#805, #998)
  * Government form moved out into ckanext-dgu repo (#1018)
  * Command-line user authorization tools extended (#1038, #1026)
  * Default user roles read from config file (#1039)

Bug fixes:
  * Mounting of filesystem (affected versions since 1.0.1) (#1040)
  * Resubmitting a package via the API (affected versions since 0.6?) (#662)
  * Open redirect (affected v1.3) (#1026)


v1.3 2011-02-18
===============
http://ckan.org/milestone/ckan-v1.3

Highlights of changes:
  * Package edit form improved:
     * field instructions (#679)
     * name autofilled from title (#778)
  * Group-based access control - Authorization Groups (#647)
  * Metadata harvest job management (#739, #884, #771)
  * CSW harvesting now uses owslib (#885)
  * Package creation authorization is configurable (#648)
  * Read-only maintenance mode (#777)
  * Stats page (#832) and importer (#950) moved out into CKAN extensions

Minor:
  * site_title and site_description config variables (#974)
  * Package creation/edit timestamps (#806)
  * Caching configuration centralised (#828)
  * Command-line tools - sysadmin management (#782)
  * Group now versioned (#231)


v1.2 2010-11-25
===============
http://ckan.org/milestone/ckan-v1.2

Highlights of changes:
  * Package edit form: attach package to groups (#652) & revealable help
  * Form API - Package/Harvester Create/New (#545)
  * Authorization extended: user groups (#647) and creation of packages (#648)
  * Plug-in interface classes (#741)
  * WordPress twentyten compatible theming (#797)
  * Caching support (ETag) (#693)
  * Harvesting GEMINI2 metadata records from OGC CSW servers (#566)

Minor:
  * New API key header (#466)
  * Group metadata now revisioned (#231)


v1.1 2010-08-10
===============
http://ckan.org/milestone/v1.1

Highlights of changes:
  * Changes to the database cause notifications via AMQP for clients (#325)
  * Pluggable search engines (#317), including SOLR (#353)
  * API is versioned and packages & groups can be referred to by invariant ID
    (#313)
  * Resource search in API (#336)
  * Visual theming of CKAN now easy (#340, #320)
  * Greater integration with external Web UIs (#335, #347, #348)
  * Plug-ins can be configured to handle web requests from specified URIs and
    insert HTML into pages.

Minor:
  * Search engine optimisations e.g. alphabetical browsing (#350)
  * CSV and JSON dumps improved (#315)


v1.0.2 2010-08-27
=================

 * Bugfix: API returns error when creating package (#432)


v1.0.1 2010-06-23
=================

Functionality:

  * API: Revision search 'since id' and revision model in API
  * API: Basic API versioning - packages specified by ID (#313)
  * Pluggable search - initial hooks
  * Customisable templates (#340) and external UI hooks (#335)

Bugfixes:

  * Revision primary key lost in migrating data (#311)
  * Local authority license correction in migration (#319)
  * I18n formatting issues
  * Web i/f searches foreign characters (#319)
  * Data importer timezone issue (#330)


v1.0 2010-05-11
===============

CKAN comes of age, having been used successfully in several deployments around
the world. 56 tickets covered in this release. See:
http://ckan.org/milestone/v1.0

Highlights of changes:

  * Package edit form: new pluggable architecture for custom forms (#281, #286)
  * Package revisions: diffs now include tag, license and resource changes
    (#303)
  * Web interface: visual overhaul (#182, #206, #214-#227, #260) including a
    tag cloud (#89)
  * i18n: completion in Web UI - now covers package edit form (#248)
  * API extended: revisions (#251, #265), feeds per package (#266)
  * Developer documentation expanded (#289, #290)
  * Performance improved and CKAN stress-tested (#201)
  * Package relationships (Read-Write in API, Read-Only in Web UI) (#253-257)
  * Statistics page (#184)
  * Group edit: add multiple packages at once (#295)
  * Package view: RDF and JSON formatted metadata linked to from package page
    (#247)

Bugfixes:

  * Resources were losing their history (#292)
  * Extra fields now work with spaces in the name (#278, #280) and
    international characters (#288)
  * Updating resources in the REST API (#293)

Infrastructural:

  * Licenses: now uses external License Service ('licenses' Python module)
  * Changesets introduced to support distributed revisioning of CKAN data - see
    doc/distributed.rst for more information.


v0.11 2010-01-25
================

Our biggest release so far (55 tickets) with lots of new features and improvements. This release also saw a major new production deployment with the CKAN software powering http://data.gov.uk/ which had its public launch on Jan 21st!

For a full listing of tickets see: <http://ckan.org/milestone/v0.11>. Main highlights:

  * Package Resource object (multiple download urls per package): each package
    can have multiple 'resources' (urls) with each resource having additional
    metadata such as format, description and hash (#88, #89, #229)
  * "Full-text" searching of packages (#187)
  * Semantic web integration: RDFization of all data plus integration with an
    online RDF store (e.g. for http://www.ckan.net/ at
    http://semantic.ckan.net/ or Talis store) (#90 #163)
  * Package ratings (#77 #194)
  * i18n: we now have translations into German and French with deployments at
    http://de.ckan.net/ and http://fr.ckan.net/ (#202)
  * Package diffs available in package history (#173)
  * Minor:

    * Package undelete (#21, #126)
    * Automated CKAN deployment via Fabric (#213)
    * Listings are sorted alphabetically (#195)
    * Add extras to rest api and to ckanclient (#158 #166)

  * Infrastructural:

    * Change to UUIDs for revisions and all domain objects
    * Improved search performance and better pagination
    * Significantly improved performance in API and WUI via judicious caching


v0.10 2009-09-30
================

  * Switch to repoze.who for authentication (#64)
  * Generic Attributes for Packages (#43)
  * Use sqlalchemy-migrate to handle db/model upgrades (#94)
  * "Groups" of packages (#105, #110, #130, #121, #123, #131)
  * Package search in the REST API (#108)
  * Full role-based access control for Packages and Groups (#93, #116, #114, #115, #117, #122, #120)
  * New CKAN logo (#72)
  * Infrastructural:

    * Upgrade to Pylons 0.9.7 (#71)
    * Convert to use formalchemy for all forms (#76)
    * Use paginate in webhelpers (#118)

  * Minor:

    * Add author and maintainer attributes to package (#91)
    * Change package state in the WUI (delete and undelete) (#126)
    * Ensure non-active packages don't show up (#119)
    * Change tags to contain any character (other than space) (#62)
    * Add Is It Open links to package pages (#74)


v0.9 2009-07-31
===============

  * (DM!) Add version attribute for package
  * Fix purge to use new version of vdm (0.4)
  * Link to changed packages when listing revision
  * Show most recently registered or updated packages on front page
  * Bookmarklet to enable easy package registration on CKAN
  * Usability improvements (package search and creation on front page)
  * Use external list of licenses from license repository
  * Convert from py.test to nosetests

v0.8 2009-04-10
===============

  * View information about package history (ticket:53)
  * Basic datapkg integration (ticket:57)
  * Show information about package openness using icons (ticket:56)
  * One-stage package create/registration (r437)
  * Reinstate package attribute validation (r437)
  * Upgrade to vdm 0.4

v0.7 2008-10-31
===============

  * Convert to use SQLAlchemy and vdm v0.3 (v. major)
  * Atom/RSS feed for Recent Changes
  * Package search via name and title
  * Tag lists show number of associated packages

v0.6 2008-07-08
===============

  * Autocompletion (+ suggestion) of tags when adding tags to a package.
  * Paginated lists for packages, tags, and revisions.
  * RESTful machine API for package access, update, listing and creation.
  * API Keys for users who wish to modify information via the REST API.
  * Update to vdm v0.2 (SQLObject) which fixes ordering of lists.
  * Better immunity to SQL injection attacks.

v0.5 2008-01-22
===============

  * Purging of a Revision and associated changes from cli and wui (ticket:37)
  * Make data available in machine-usable form via sql dump (ticket:38)
  * Upgrade to Pylons 0.9.6.* and deploy (ticket:41)
  * List and search tags (ticket:33)
  * (bugfix) Manage reserved html characters in urls (ticket:40)
  * New spam management utilities including (partial) blacklist support

v0.4 2007-07-04
===============

  * Preview support when editing a package (ticket:36).
  * Correctly list IP address of of not logged in users (ticket:35).
  * Improve read action for revision to list details of changed items (r179).
  * Sort out deployment using modpython.

v0.3 2007-04-12
===============

  * System now in a suitable state for production deployment as a beta
  * Domain model versioning via the vdm package (currently released separately)
  * Basic Recent Changes listing log messages
  * User authentication (login/logout) via open ID
  * License page
  * Myriad of small fixes and improvements

v0.2 2007-02
============

  * Complete rewrite of ckan to use pylons web framework
  * Support for full CRUD on packages and tags
  * No support for users (authentication)
  * No versioning of domain model objects

v0.1 2006-05
============

NB: not an official release

  * Almost functional system with support for persons, packages
  * Tag support only half-functional (tags are per package not global)
  * Limited release and file support
