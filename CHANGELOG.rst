.. This tocdepth stops Sphinx from putting every subsection title in this file
   into the master table of contents.

:tocdepth: 1

---------
Changelog
---------

v.2.9.0 TBA
==================

 * When upgrading from previous CKAN versions, the Activity Stream needs a
   migrate_package_activity.py running for displaying the history of dataset
   changes. This can be performed while CKAN is running or stopped (whereas the
   standard `paster db upgrade` migrations need CKAN to be stopped). Ideally it
   is run before CKAN is upgraded, but it can be run afterwards. If running
   previous versions or this version of CKAN, download and run
   migrate_package_activity.py like this:

     cd /usr/lib/ckan/default/src/ckan/
     wget https://raw.githubusercontent.com/ckan/ckan/3484_revision_ui_removal2/ckan/migration/migrate_package_activity.py
     wget https://raw.githubusercontent.com/ckan/ckan/3484_revision_ui_removal2/ckan/migration/revision_legacy_code.py
     python migrate_package_activity.py -c /etc/ckan/production.ini

   Future versions of CKAN are likely to need a slightly different procedure.
   Full info about this migration is found here:
   https://github.com/ckan/ckan/wiki/Migrate-package-activity

 * A full history of dataset changes is now displayed in the Activity Stream to
   admins, and optionally to the public. By default this is enabled for new
   installs, but disabled for sites which upgrade (just in case the history is
   sensitive). When upgrading, open data CKANs are encouraged to make this
   history open to the public, by setting this in production.ini:
   ``ckan.auth.public_activity_stream_detail = true`` (#3972)

Minor changes:

 * For navl schemas, the 'default' validator no longer applies the default when
   the value is False, 0, [] or {} (#4448)
 * If you've customized the schema for package_search, you'll need to add to it
   the limiting of ``row``, as per default_package_search_schema now does (#4484)
 * Several logic functions now have new upper limits to how many items can be
   returned, notably ``group_list``, ``organization_list`` when
   ``all_fields=true``, ``datastore_search`` and ``datastore_search_sql``.
   These are all configurable. (#4484, #4562)

Bugfixes:

 * Action function "datastore_search" would calculate the total, even if you
   set include_total=False (#4448)

Removals and deprecations:

 * Revision and History UI is removed: `/revision/*` & `/dataset/{id}/history`
   in favour of `/dataset/changes/` visible in the Activity Stream. (#3972)
 * Logic functions removed:
   ``dashboard_activity_list_html`` ``organization_activity_list_html``
   ``user_activity_list_html`` ``package_activity_list_html``
   ``group_activity_list_html`` ``organization_activity_list_html``
   ``recently_changed_packages_activity_list_html``
   ``dashboard_activity_list_html`` ``activity_detail_list`` (#4627/#3972)
 * ``model.ActivityDetail`` is no longer used and will be removed in the next
   CKAN release. (#3972)
 * ``c.action`` and ``c.controller`` variables should be avoided.
   ``ckan.plugins.toolkit.get_endpoint`` can be used instead. This function
   returns tuple of two items(depending on request handler):
   1. Flask blueprint name / Pylons controller name
   2. Flask view name / Pylons action name
   In some cases, Flask blueprints have names that are differs from their
   Pylons equivalents. For example, 'package' controller is divided between
   'dataset' and 'resource' blueprints. For such cases you may need to perform
   additional check of returned value:

   >>> if toolkit.get_endpoint()[0] in ['dataset', 'package']:
   >>>     do_something()

   In this code snippet, will be called if current request is handled via Flask's
   dataset blueprint in CKAN>=2.9, and, in the same time, it's still working for
   Pylons package controller in CKAN<2.9

v.2.8.2 2018-12-12
==================

General notes:
 * This version requires a requirements upgrade on source installations
 * Note: This version does not requires a database upgrade
 * Note: This version does not require a Solr schema upgrade

Fixes:

* Strip full URL on uploaded resources before saving to DB (`#4382 <https://github.com/ckan/ckan/issues/4382>`_)
* Fix user not being defined in check_access function (`#4574 <https://github.com/ckan/ckan/issues/4574>`_)
* Remove html5 shim from stats extension (`#4236 <https://github.com/ckan/ckan/issues/4236>`_)
* Fix for datastore_search distinct=true option (`#4236 <https://github.com/ckan/ckan/issues/4236>`_)
* Fix edit slug button (`#4379 <https://github.com/ckan/ckan/issues/4379>`_)
* Don't re-register plugin helpers on flask_app (`#4414 <https://github.com/ckan/ckan/issues/4414>`_)
* Fix for Resouce View Re-order (`#4416 <https://github.com/ckan/ckan/issues/4416>`_)
* autocomplete.js: fix handling of comma key codes (`#4421 <https://github.com/ckan/ckan/issues/4421>`_)
* Flask patch update (`#4426 <https://github.com/ckan/ckan/issues/4426>`_)
* Allow plugins to define multiple blueprints (`#4495 <https://github.com/ckan/ckan/issues/4495>`_)
* Fix i18n API encoding (`#4505 <https://github.com/ckan/ckan/issues/4505>`_)
* Allow to defined legacy route mappings as a dict in config (`#4521 <https://github.com/ckan/ckan/issues/4521>`_)
* group_patch does not reset packages (`#4557 <https://github.com/ckan/ckan/issues/4557>`_)

v.2.8.1 2018-07-25
==================

General notes:
 * Note: This version does not requires a requirements upgrade on source installations
 * Note: This version does not requires a database upgrade
 * Note: This version does not require a Solr schema upgrade

Fixes:

 * "Add Filter" Performance Issue (`#4162 <https://github.com/ckan/ckan/issues/4162>`_)
 * Error handler update (`#4257 <https://github.com/ckan/ckan/issues/4257>`_)
 * "New view" button does not work (`#4260 <https://github.com/ckan/ckan/issues/4260>`_)
 * Upload logo is not working (`#4262 <https://github.com/ckan/ckan/issues/4262>`_)
 * Unable to pip install ckan (`#4271 <https://github.com/ckan/ckan/issues/4271>`_)
 * The "License" Icon in 2.8 is wrong (`#4272 <https://github.com/ckan/ckan/issues/4272>`_)
 * Search - input- border color is overly specific in CSS (`#4273 <https://github.com/ckan/ckan/issues/4273>`_)
 * Site logo image does not scale down when very large (`#4283 <https://github.com/ckan/ckan/issues/4283>`_)
 * Validation Error on datastore_search when sorting timestamp fields (`#4288 <https://github.com/ckan/ckan/issues/4288>`_)
 * Undocumented changes breaking error_document_template (`#4303 <https://github.com/ckan/ckan/issues/4303>`_)
 * Internal server error when viewing /dashboard when logged out (`#4305 <https://github.com/ckan/ckan/issues/4305>`_)
 * Missing c.action attribute in 2.8.0 templates (`#4310 <https://github.com/ckan/ckan/issues/4310>`_)
 * [multilingual] AttributeError: '_Globals' object has no attribute 'fields' (`#4338 <https://github.com/ckan/ckan/issues/4338>`_)
 * `search` legacy route missing (`#4346 <https://github.com/ckan/ckan/issues/4346>`_)


v.2.8.0 2018-05-09
==================

General notes:
 * This version requires a requirements upgrade on source installations
 * This version requires a database upgrade
 * This version requires a Solr schema upgrade
 * This version requires re-running the ``datastore set-permissions`` command
   (assuming you are using the DataStore). See: :ref:`datastore-set-permissions`

   Otherwise new and updated datasets will not be searchable in DataStore and
   the logs will contain this error::

      ProgrammingError: (psycopg2.ProgrammingError) function populate_full_text_trigger() does not exist

   CKAN developers should also re-run set-permissions on the test database:
   :ref:`datastore-test-set-permissions`

 * There are several old features being officially deprecated starting from
   this version. Check the *Deprecations* section to be prepared.

Major changes:
 * New revamped frontend templates based on Bootstrap 3, see "Changes and deprecations" (#3547)
 * Allow datastore_search_sql on private datasets (#2562)
 * New Flask blueprints migrated from old Pylons controllers: user, dashboard, feeds, admin and home (#3927, #3870, #3775, #3762)
 * Improved support for custom groups and organization types (#4032)
 * Hide user details to anonymous users (#3915)

Minor changes:
 * Allow chaining of authentication functions (#3679)
 * Show custom dataset types in search pages (#3807)
 * Overriding datastore authorization system (#3679)
 * Standardize on url_for (#3831)
 * Deprecate notify_after_commit (#3633)
 *  _mail_recipient header override (#3781)
 * Restrict access to member forms (#3684)
 * Clean up template rendering code (#3923)
 * Permission labels are indexed by type text in SOLR (#3863)
 * CLI commands require a Flask test request context (#3760)
 * Allow IValidator to override existing validators (#3865)
 * Shrink datastore_create response size (#3810)
 * Stable version URLs CKAN for documentation (#4209)
 * API Documentation update (#4136)
 * Documentation of Data Dictionary  (#3989)
 * Remove datastore legacy mode (#4041)
 * Map old Pylons routes to Flask ones (#4066)

Bug fixes:
 * File uploads don't work on new Flask based API (#3869)
 * {% ckan_extends %} not working on templates served by Flask (#4044)
 * Problems in background workers with non-core database relations (#3606)
 * Render_datetime can't handle dates before year 1900 (#2228)
 * DatapusherPlugin implementation of notify() can call 'datapusher_submit' multiple times (#2334)
 * Dataset creation page generates incorrect URLs with Chrome autocomplete (#2501)
 * Search buttons need accessible labels (#2550)
 * Column name length limit for datastore upload (#2804)
 * #2373: Do not validate packages or resources from database to views (#3016)
 * Creation of dataset - different behaviour between Web API & CKAN Interface functionality (#3528)
 * Redirecting to same page in non-root hosted ckan adds extra root_path to url  (#3499)
 * Beaker 1.8.0 exception when the code is served from OSX via Vagrant (#3512)
 * Add "Add Dataset" button to user's and group's page (#2794)
 * Some links in CKAN is not reachable (#2898)
 * Exception when specifying a directory in the ckan.i18n_directory option (#3539)
 * Resource view filter user filters JS error (#3590)
 * Recaptcha v1 will stop working 2018-3-31 (#4061)
 * "Testing coding standards" page in docs is missing code snippets (#3635)
 * Followers count not updated immediately on UI (#3639)
 * Increase jQuery version (#3665)
 * Search icon on many pages is not properly vertically aligned (#3654)
 * Datatables view can't be used as a default view (#3669)
 * Resource URL is not validated on create/update (#3660)
 * Upload to Datastore tab shows incorrect time at Upload Log (#3588)
 * Filter results button is not working (#3593)
 * Broken link in "Upgrading CKAN’s dependencies" doc page (#3637)
 * Default logo image not properly saved (#3656)
 * Activity test relies on datetime.now() (#3644)
 * Info block text for Format field not properly aligned in resource form page (#3663)
 * Issue upon creating new organization/group through UI form (#3661)
 * In API docs "package_create" lists "owner_org" as optional (#3647)
 * Embed modal window not working (#3731)
 * Frontent build command does not work on master (#3688)
 * Loading image duplicated  (#3716)
 * Datastore set-up error - logging getting in the way (#3694)
 * Registering a new account redirects to an unprefixed url (#3834)
 * Exception in search page when not authorized (#4081)
 * Datastore full-text-search column is populated by postgres trigger rather than python (#3785)
 * Datastore dump results are not the same as data in database (#4150)
 * Adding filter at resoruce preview doesn't work while site is setup with ckan.root_path param (#4140)
 * No such file or directory: '/usr/lib/ckan/default/src/ckan/requirement-setuptools.txt' during installation from source (#3641)
 * Register user form missing required field indicators (#3658)
 * Datastore full-text-search column is populated by postgres trigger rather than python  (#3786)
 * Add missing major changes to change log (#3799)
 * Paster/CLI config-tool requires _get_test_app which in turn requires a dev-only dependency (#3806)
 * Change log doesn't mention necessary Solr scheme upgrade (#3851)
 * TypeError: expected byte string object, value of type unicode found (#3921)
 * CKAN's state table clashes with PostGIS generated TIGER state table (#3929)
 * [Docker] entrypoint initdb.d sql files copied to root (#3939)
 * DataStore status page throws TypeError - Bleach upgrade regression (#3968)
 * Source install error with who.ini (#4020)
 * making a JSONP call to the CKAN API returns the wrong mime type (#4022)
 * Deleting a resource sets datastore_active=False to all resources and overrides their extras (#4042)
 * Deleting first Group and Organization custom field is not possible (#4094)

Changes and deprecations:
 * The default templates included in CKAN core have been updated to use Bootstrap 3. Extensions
   implementing custom themes are encouraged to update their templates, but they can still
   make CKAN load the old Bootstrap 2 templates during the transition using the following
   configuration options::

        ckan.base_public_folder = public-bs2
        ckan.base_templates_folder = templates-bs2

 * The API versions 1 and 2 (also known as the REST API), ie ``/api/rest/*`` have been
   completely removed in favour of the version 3 (action API, ``/api/action/*``).
 * The old Celery based background jobs have been removed in CKAN 2.8 in favour of the new RQ based
   jobs (http://docs.ckan.org/en/latest/maintaining/background-tasks.html). Extensions can still
   of course use Celery but they will need to handle the management themselves.
 * After introducing dataset blueprint, `h.get_facet_items_dict` takes search_facets as second argument.
   This change is aimed to reduce usage of global variables in context. For a while, it has default value
   of None, in which case, `c.search_facets` will be used. But all template designers are strongly advised
   to specify this argument explicitly, as in future it'll become required.
 * The ``ckan.recaptcha.version`` config option is now removed, since v2 is the only valid version now (#4061)

v2.7.5 2018-12-12
=================

  * Strip full URL on uploaded resources before saving to DB (`#4382 <https://github.com/ckan/ckan/issues/4382>`_)
  * Fix for datastore_search distinct=true option (`#4236 <https://github.com/ckan/ckan/issues/4236>`_)
  * Fix edit slug button (`#4379 <https://github.com/ckan/ckan/issues/4379>`_)
  * Don't re-register plugin helpers on flask_app (`#4414 <https://github.com/ckan/ckan/issues/4414>`_)
  * Fix for Resouce View Re-order (`#4416 <https://github.com/ckan/ckan/issues/4416>`_)
  * autocomplete.js: fix handling of comma key codes (`#4421 <https://github.com/ckan/ckan/issues/4421>`_)
  * Flask patch update (`#4426 <https://github.com/ckan/ckan/issues/4426>`_)
  * Allow plugins to define multiple blueprints (`#4495 <https://github.com/ckan/ckan/issues/4495>`_)
  * Fix i18n API encoding (`#4505 <https://github.com/ckan/ckan/issues/4505>`_)
  * Allow to defined legacy route mappings as a dict in config (`#4521 <https://github.com/ckan/ckan/issues/4521>`_)
  * group_patch does not reset packages (`#4557 <https://github.com/ckan/ckan/issues/4557>`_)

v2.7.4 2018-05-09
=================

 * Adding filter at resoruce preview doesn't work while site is setup with ckan.root_path param (#4140)
 * Datastore dump results are not the same as data in database (#4150)

v2.7.3 2018-03-15
=================

General notes:
 * As with all patch releases this one does not include requirement changes.
   However in some scenarios you might encounter the following error while
   installing or upgrading this version of CKAN::

     Error: could not determine PostgreSQL version from '10.2'

   This is due to a bug in the psycopg2 version pinned to the release. To solve
   it, upgrade psycopg2 with the following command::

     pip install --upgrade psycopg2==2.7.3.2

 * This release does not require a Solr schema upgrade, but if you are having the
   issues described in #3863 (datasets wrongly indexed in multilingual setups),
   you can upgrade the Solr schema and reindex to solve them.

 * #3422 (implemented in #3425) introduced a major bug where if a resource was
   deleted and the DataStore was active extras from all resources on the site where
   changed. This is now fixed as part of this release but if your database is already
   affected you will need to run a script to restore the extras to their
   previous state. Remember, you only need to run the script if all the following are
   true:

   1. You are currently running CKAN 2.7.0 or 2.7.2, and
   2. You have enabled the DataStore, and
   3. One or more resources with data on the DataStore have been deleted (or you
      suspect they might have been)

   If all these are true you can run the following script to restore the extras to
   their previous state:

   https://github.com/ckan/ckan/blob/dev-v2.7/scripts/4042_fix_resource_extras.py

   This issue is described in #4042

Fixes:
 * Fix toggle bars header icon (#3880)
 * Change CORS header keys and values to string instead of unicode (#3855)
 * Fix cors header when all origins are allowed (#3898)
 * Update SOLR schema.xml reference in Dockerfile
 * Build local SOLR container by default
 * Create datastore indexes only if they are not exist
 * Properly close file responses
 * Use javascript content-type for jsonp responses (#4022)
 * Add Data Dictionary documentation (#3989)
 * Fix SOLR index delete_package implementation
 * Add second half of DataStore set-permissions command(Docs)
 * Fix extras overriding for removed resources (#4042)
 * Return a 403 if not authorized on the search page (#4081)
 * Add support for user/pass for Solr as ENV var
 * Change permission_labels type to string in schema.xml (#3863)
 * Disallow solr local parameters
 * Improve text view rendering
 * Update Orgs/Groups logic for custom fields delete and update (#4094)
 * Upgrade Solr Docker image

v2.7.2 2017-09-28
=================

 * Include missing minified JavaScript files

v2.7.1 2017-09-27
=================

 * add field_name to image_upload macro when uploading resources (#3766)
 * Add some missing major changes to change log. (#3799)
 * _mail_recipient header override (#3781)
 * skip url parsing in redirect (#3499)
 * Fix multiple errors in i18n of JS modules (#3590)
 * Standardize on url_for on popup (#3831)

v2.7.0 2017-08-02
=================

General notes:
 * Starting from this version, CKAN requires at least Postgres 9.3
 * Starting from this version, CKAN requires a Redis database. Please
   refer to the new `ckan.redis.url
   <http://docs.ckan.org/en/ckan-2.7.0/maintaining/configuration.html#ckan-redis-url>`_
   configuration option.
 * This version requires a requirements upgrade on source installations
 * This version requires a database upgrade
 * This version requires a Solr schema upgrade
 * There are several old features being officially deprecated starting from
   this version. Check the *Deprecations* section to be prepared.

Major changes:
 * New datatables_view resource view plugin for tabular data (#3444)
 * IDataStoreBackend plugins for replacing the default DataStore Postgres backend (#3437)
 * datastore_search new result formats and performance improvements (#3523)
 * PL/PGSQL triggers for DataStore tables (#3428)
 * DataStore dump CLI commands (#3384)
 * Wrap/override actions defined in other plugins (#3494)
 * DataStore table data dictionary stored as postgres comments (#3414)
 * Common session object for Flask and Pylons (#3208)
 * Rename deleted datasets when they conflict with new ones (#3370)
 * DataStore dump more formats: CSV, TSV, XML, JSON; BOM option (#3390)
 * Common requests code for Flask and Pylons (#3212)
 * Generate complete datastore dump files (#3344)
 * A new system for asynchronous background jobs (#3165)

Minor changes:
 * Renamed example theme plugin (#3576)
 * Localization support for groups (#3559)
 * Create new resource views when format changes (#3515)
 * Email field validation (#3568)
 * datastore_run_triggers sysadmin-only action to apply triggers to existing data (#3565)
 * Docs updated for Ubuntu 16.04 (#3544)
 * Upgrade leaflet to 0.7.7 (#3534)
 * Datapusher CLI always-answer-yes option (#3524)
 * Added docs for all plugin interfaces (#3519)
 * DataStore dumps nested columns as JSON (#3487)
 * Faster/optional datastore_search total calculation (#3467)
 * Faster group_activity_query (#3466)
 * Faster query performance (#3430)
 * Marked remaining JS strings translatable (#3423)
 * Upgrade font-awesome to 4.0.3 (#3400)
 * group/organization_show include_dataset_count option (#3385)
 * image_formats config option for image viewer (#3380)
 * click may now be used for CLI interfaces: use load_config instead of CkanCommand (#3384)
 * package_search option to return only names/ids (#3427)
 * user_list all_fields option (#3353)
 * Error controller may now be overridden (#3340)
 * Plural translations in JS (#3211)
 * Support JS translations in extensions (#3272)
 * Requirements upgraded (#3305)
 * Dockerfile updates (#3295)
 * Fix activity test to use utcnow (#3644)
 * Changed required permission from 'update' to 'manage_group' (#3631)
 * Catch invalid sort param exception (#3630)
 * Choose direction of recreated package relationship depending on its type (#3626)
 * Fix render_datetime for dates before year 1900 (#3611)
 * Fix KeyError in 'package_create' (#3027)
 * Allow slug preview to work with autocomplete fields (#2501)
 * Fix filter results button not working for organization/group (#3620)
 * Allow underscores in URL slug preview on create dataset (#3612)
 * Fallback to po file translations on ``h.get_translated()`` (#3577)
 * Fix Fanstatic URL on non-root installs (#3618)
 * Fixed escaping issues with ``helpers.mail_to`` and datapusher logs
 * Autocomplete fields are more responsive - 300ms timeout instead of 1s (#3693)
 * Fixed dataset count display for groups (#3711)
 * Restrict access to form pages (#3684)
 * Render_datetime can handle dates before year 1900 (#2228)

API changes:
 * ``organization_list_for_user`` (and the ``h.organizations_available()``
   helper) now return all organizations a user belongs to regardless of
   capacity (Admin, Editor or Member), not just the ones where she is an
   administrator (#2457)
 * ``organization_list_for_user`` (and the ``h.organizations_available()``
   helper) now default to not include package_count. Pass
   include_dataset_count=True if you need the package_count values.
 * ``resource['size']`` will change from string to long integer (#3205)
 * Font Awesome has been upgraded from version 3.2.1 to 4.0.3 .Please refer to
   https://github.com/FortAwesome/Font-Awesome/wiki/Upgrading-from-3.2.1-to-4
   to upgrade your code accordingly if you are using custom themes.

Deprecations:
 * The API versions 1 and 2 (also known as the REST API, ie ``/api/rest/*`` will removed
   in favour of the version 3 (action API, ``/api/action/*``), which was introduced in
   CKAN 2.0. The REST API will be removed on CKAN 2.8.
 * The default theme included in CKAN core will switch to use Bootstrap 3 instead of
   Bootstrap 2 in CKAN 2.8. The current Bootstrap 2 based templates will still be included
   in the next CKAN versions, so existing themes will still work. Bootstrap 2 templates will
   be eventually removed though, so instances are encouraged to update their themes using
   the available documentation (https://getbootstrap.com/migration/)
 * The activity stream related actions ending with ``*_list`` (eg ``package_activity_list``)
   and ``*_html`` (eg ``package_activity_list_html``) will be removed in CKAN 2.8 in favour of
   more efficient alternatives and are now deprecated.
 * The legacy revisions controller (ie ``/revisions/*``) will be completely removed in CKAN 2.8.
 * The old Celery based background jobs will be removed in CKAN 2.8 in favour of the new RQ based
   jobs (http://docs.ckan.org/en/latest/maintaining/background-tasks.html). Extensions can still
   of course use Celery but they will need to handle the management themselves.

v2.6.7 2018-12-12
=================

  * Fix for Resouce View Re-order (`#4416 <https://github.com/ckan/ckan/issues/4416>`_)
  * autocomplete.js: fix handling of comma key codes (`#4421 <https://github.com/ckan/ckan/issues/4421>`_)
  * group_patch does not reset packages (`#4557 <https://github.com/ckan/ckan/issues/4557>`_)

v2.6.6 2018-05-09
=================

* Adding filter at resoruce preview doesn't work while site is setup with ckan.root_path param (#4140)
* Stable version URLs CKAN for documentation (#4209)
* Add Warning in docs sidebar (#4209)

v2.6.5 2018-03-15
=================

Note: This version requires a database upgrade

* Activity Time stored in UTC (#2882)
* Migration script to adjust current activity timestamps to UTC
* Change CORS header keys and values to string instead of unicode (#3855)
* Fix cors header when all origins are allowed (#3898)
* Update SOLR schema.xml reference in Dockerfile
* Build local SOLR container by default
* Create datastore indexes only if they don't exist
* Properly close file responses
* Use javascript content-type for jsonp responses (#4022)
* Fix SOLR index delete_package implementation
* Add second half of DataStore set-permissions command (Docs)
* Return a 403 if not authorized on the search page (#4081)
* Add support for user/pass for Solr as ENV var
* Disallow solr local parameters
* Improve text view rendering
* Update Orgs/Groups logic for custom fields delete and update (#4094)

v2.6.4 2017-09-27
=================

* Mail recepient header override (#3781)
* Skip url parsing in redirect (#3499)
* Support non root for fanstatic (#3618)

v2.6.3 2017-08-02
=================

* Fix in organization / group form image URL field (#3661)
* Fix activity test to use utcnow (#3644)
* Changed required permission from 'update' to 'manage_group' (#3631)
* Catch invalid sort param exception (#3630)
* Choose direction of recreated package relationship depending on its type (#3626)
* Fix render_datetime for dates before year 1900 (#3611)
* Fix KeyError in 'package_create' (#3027)
* Allow slug preview to work with autocomplete fields (#2501)
* Fix filter results button not working for organization/group (#3620)
* Allow underscores in URL slug preview on create dataset (#3612)
* Create new resource view if resource format changed (#3515)
* Fixed escaping issues with `helpers.mail_to` and datapusher logs
* Autocomplete fields are more responsive - 300ms timeout instead of 1s (#3693)
* Fixed dataset count display for groups (#3711)
* Restrict access to form pages (#3684)

v2.6.2 2017-03-22
=================

* Use fully qualified urls for reset emails (#3486)
* Fix edit_resource for resource with draft state (#3480)
* Tag fix for group/organization pages (#3460)
* Setting of datastore_active flag moved to separate function (#3481)

v2.6.1 2017-02-22
=================

 * Fix DataPusher being fired multiple times (`#3245 <https://github.com/ckan/ckan/issues/3245>`_)
 * Use the url_for() helper for datapusher URLs (`#2866 <https://github.com/ckan/ckan/issues/2866>`_)
 * Resource creation date use datetime.utcnow() (`#3447 <https://github.com/ckan/ckan/issues/3447>`_)
 * Fix locale error when using fix ckan.root_path
 * `render_markdown` breaks links with ampersands
 * Check group name and id during package creation
 * Use utcnow() on dashboard_mark_activities_old (`#3373 <https://github.com/ckan/ckan/issues/3373>`_)
 * Fix encoding error on DataStore exception
 * Datastore doesn't add site_url to resource created via API (`#3189 <https://github.com/ckan/ckan/issues/3189>`_)
 * Fix memberships after user deletion (`#3265 <https://github.com/ckan/ckan/issues/3265>`_)
 * Remove idle database connection (`#3260 <https://github.com/ckan/ckan/issues/3260>`_)
 * Fix package_owner_org_update action when called via the API (`#2661 <https://github.com/ckan/ckan/issues/2661>`_)
 * Fix French locale (`#3327 <https://github.com/ckan/ckan/issues/3327>`_)
 * Updated translations

v2.6.0 2016-11-02
=================

Note: Starting from this version, CKAN requires at least Python 2.7 and Postgres 9.2

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version does not require a Solr schema upgrade (You may want to
         upgrade the schema if you want to target Solr>=5, see `#2914 <https://github.com/ckan/ckan/issues/2914>`_)

Major:
 * Private datasets are now included in the default dataset search results (`#3191 <https://github.com/ckan/ckan/pull/3191>`_)
 * package_search API action now has an include_private parameter (`#3191 <https://github.com/ckan/ckan/pull/3191>`_)

Minor:
 * Make resource name default to file name (`#1372 <https://github.com/ckan/ckan/issues/1372>`_)
 * Customizable email templates  (`#1527 <https://github.com/ckan/ckan/issues/1527>`_)
 * Change solrpy library to pysolr (`#2352 <https://github.com/ckan/ckan/pull/2352>`_)
 * Cache SQL query results (`#2353 <https://github.com/ckan/ckan/issues/2353>`_)
 * File Upload UX improvements (`#2604 <https://github.com/ckan/ckan/issues/2604>`_)
 * Helpers for multilingual fields (`#2678 <https://github.com/ckan/ckan/issues/2678>`_)
 * Improve Extension translation docs (`#2783 <https://github.com/ckan/ckan/pull/2783>`_)
 * Decouple configuration from Pylons (`#3163 <https://github.com/ckan/ckan/pull/3163>`_)
 * toolkit: add h, StopOnError, DefaultOrganizationForm (`#2835 <https://github.com/ckan/ckan/pull/2835>`_)
 * Remove Genshi support (`#2833 <https://github.com/ckan/ckan/issues/2833>`_)
 * Make resource URLs optional (`#2844 <https://github.com/ckan/ckan/pull/2844>`_)
 * Use 403 when actions are forbidden, not 401  (`#2846 <https://github.com/ckan/ckan/pull/2846>`_)
 * Upgrade requirements version (`#3004 <https://github.com/ckan/ckan/pull/3004>`_, `#3005 <https://github.com/ckan/ckan/pull/3005>`_)
 * Add icons sources (`#3048 <https://github.com/ckan/ckan/pull/3048>`_)
 * Remove lib/dumper (`#2879 <https://github.com/ckan/ckan/pull/2879>`_)
 * ckan.__version__ available as template helper (`#3103 <https://github.com/ckan/ckan/pull/3103>`_)
 * Remove `site_url_nice` from app_globals (`#3117 <https://github.com/ckan/ckan/pull/3117>`_)
 * Remove `e.message` deprecation warning when running tests (`#3121 <https://github.com/ckan/ckan/pull/3121>`_)
 * Drop Python 2.6 support (`#3126 <https://github.com/ckan/ckan/issues/3126>`_)
 * Update Recline version (`#3184 <https://github.com/ckan/ckan/pull/3184>`_)
 * Refactor config/middleware.py to more closely match poc-flask-views (`#3116 <https://github.com/ckan/ckan/pull/3116>`_)
 * Creation of datasets sources with no organization specified (`#3046 <https://github.com/ckan/ckan/issues/3046>`_)

Bug fixes:
 * DataPusher called multiple times when creating a dataset (`#2856 <https://github.com/ckan/ckan/issues/2856>`_)
 * Default view is re-added when removed before DataStore upload is complete (`#3011 <https://github.com/ckan/ckan/issues/3011>`_)
 * "Data API" button disappears on resource page after empty update (`#3012 <https://github.com/ckan/ckan/issues/3012>`_)
 * Uncaught email exceptions on user invite (`#3077 <https://github.com/ckan/ckan/pull/3077>`_)
 * Resource view description is not rendered as Markdown (`#3128 <https://github.com/ckan/ckan/issues/3128>`_)
 * Fix broken html5lib dependency (`#3180 <https://github.com/ckan/ckan/pull/3180>`_)
 * ZH_cn translation formatter fix (`#3238 <https://github.com/ckan/ckan/pull/3238>`_)
 * Incorrect i18n-paths in extension's setup.cfg (`#3275 <https://github.com/ckan/ckan/issues/3275>`_)
 * Changing your user name produces an error and logs you out (`#2394 <https://github.com/ckan/ckan/issues/2394>`_)
 * Fix "Load more" functionality in the dashboard (`#2346 <https://github.com/ckan/ckan/issues/2346>`_)
 * Fix filters not working when embedding a resource view (`#2657 <https://github.com/ckan/ckan/issues/2657>`_)
 * Proper sanitation of header name on SlickGrid view (`#2923 <https://github.com/ckan/ckan/issues/2923>`_)
 * Fix unicode error when indexing field of type JSON (`#2969 <https://github.com/ckan/ckan/issues/2969>`_)
 * Fix group feeds returning no datasets (`#2955 <https://github.com/ckan/ckan/issues/2955>`_)
 * Replace MapQuest tiles in Recline with Stamen Terrain (`#3162 <https://github.com/ckan/ckan/issues/3162>`_)
 * Fix bulk operations not taking effect (`#3199 <https://github.com/ckan/ckan/pull/3199>`_)
 * Raise validation errors on group/org_member_create (`#3108 <https://github.com/ckan/ckan/pull/3108>`_)
 * Incorrect warnings when ckan.views.default_views is empty (`#3093 <https://github.com/ckan/ckan/issues/3093>`_)
 * Don't show deleted users/datasets on member_list (`#3078 <https://github.com/ckan/ckan/pull/3078>`_)
 * Fix Tag pagination widget styling (`#2399 <https://github.com/ckan/ckan/issues/2399>`_)
 * Fix package_owner_org_update standalone (`#2661 <https://github.com/ckan/ckan/issues/2661>`_)
 * Don't template fanstatic error pages (`#2770 <https://github.com/ckan/ckan/pull/2770>`_)
 * group_controller() on IGroupForm not in interface (`#2771 <https://github.com/ckan/ckan/issues/2771>`_)
 * Fix assert_true to test for message in response (`#2802 <https://github.com/ckan/ckan/pull/2802>`_)
 * Add user parameter to paster profile command (`#2815 <https://github.com/ckan/ckan/pull/2815>`_)
 * make context['user'] always username or None (`#2817 <https://github.com/ckan/ckan/pull/2817>`_)
 * remove some deprecated compatibility hacks (`#2818 <https://github.com/ckan/ckan/pull/2818>`_)
 * Param use_default_schema does not work on package_search (`#2848 <https://github.com/ckan/ckan/pull/2848>`_)
 * Sanitize offset when listing group activity (`#2859 <https://github.com/ckan/ckan/issues/2859>`_)
 * Incorrect 'download resource' hyperlink when a resource is unable to upload to datastore  (`#2873 <https://github.com/ckan/ckan/issues/2873>`_)
 * Resolve datastore_delete erasing the database when filters was blank. (`#2885 <https://github.com/ckan/ckan/pull/2885>`_)
 * DomainObject.count() doesn't return count (`#2919 <https://github.com/ckan/ckan/pull/2919>`_)
 * Fix response code test failures (`#2931 <https://github.com/ckan/ckan/pull/2931>`_)
 * Fixed the url_for_* helpers when both SCRIPT_NAME and ckan.root_path are defined (`#2936 <https://github.com/ckan/ckan/pull/2936>`_)
 * Escape special characters in password while db loading (`#2952 <https://github.com/ckan/ckan/issues/2952>`_)
 * Fix redirect not working with non-root (`#2968 <https://github.com/ckan/ckan/pull/2968>`_)
 * Group pagination does not preserve sort order (`#2981 <https://github.com/ckan/ckan/issues/2981>`_)
 * Remove LazyJSONObject (`#2983 <https://github.com/ckan/ckan/pull/2983>`_)
 * Deleted users appear in sysadmin user lists (`#2988 <https://github.com/ckan/ckan/issues/2988>`_)
 * Server error at /organization if not authorized to list organizations (`#2990 <https://github.com/ckan/ckan/issues/2990>`_)
 * Slow page rendering when using lots of snippets (`#3000 <https://github.com/ckan/ckan/pull/3000>`_)
 * Only allow JSONP callbacks on GET requests (`#3002 <https://github.com/ckan/ckan/pull/3002>`_)
 * Attempting to access non-existing helpers should raise HelperException (`#3041 <https://github.com/ckan/ckan/issues/3041>`_)
 * Deprecate h.url, make it use h.url_for internally (`#3055 <https://github.com/ckan/ckan/pull/3055>`_)
 * Tests fail when LANG environment variable is set to German (`#3060 <https://github.com/ckan/ckan/issues/3060>`_)
 * Fix pagination style (CSS) (`#3067 <https://github.com/ckan/ckan/pull/3067>`_)
 * Login fails with 404 when using root_path (`#3089 <https://github.com/ckan/ckan/issues/3089>`_)
 * Resource view description is not rendered as Markdown (`#3128 <https://github.com/ckan/ckan/issues/3128>`_)
 * Clarify package_relationship_update documentation (`#3132 <https://github.com/ckan/ckan/pull/3132>`_)
 * `q` parameter in followee_list action has no effect (`#3167 <https://github.com/ckan/ckan/pull/3167>`_)
 * Zh cn translation formatter fix (`#3238 <https://github.com/ckan/ckan/pull/3238>`_)
 * Users are not removed in related tables if the main user entry is deleted (`#3265 <https://github.com/ckan/ckan/issues/3265>`_)

API changes and deprecations:
 * Replace `c.__version__` with new helper `h.ckan_version()` (`#3103 <https://github.com/ckan/ckan/pull/3103>`_)

v2.5.9 2018-05-09
=================

* Adding filter at resoruce preview doesn't work while site is setup with ckan.root_path param (#4140)
* Add Warning in docs sidebar (#4209)
* Point API docs to stable URL (#4209)

v2.5.8 2018-03-15
=================

Note: This version requires a database upgrade

* Fix language switcher
* Activity Time stored in UTC (#2882)
* Migration script to adjust current activity timestamps to UTC
* Change CORS header keys and values to string instead of unicode (#3855)
* Fix cors header when all origins are allowed (#3898)
* Create datastore indexes only if they are not exist
* Use javascript content-type for jsonp responses (#4022)
* Fix SOLR index delete_package implementation
* Add second half of DataStore set-permissions command(Docs)
* Update SOLR client (pysolr -> solrpy)
* Return a 403 if not authorized on the search page (#4081)
* Add support for user/pass for Solr as ENV var
* Disallow solr local parameters
* Improve text view rendering
* Update Orgs/Groups logic for custom fields delete and update (#4094)

v2.5.7 2017-09-27
=================

* Allow overriding email headers (#3781)
* Support non-root instances on fanstatic (#3618)
* Add missing close button on organization page (#3814)

v2.5.6 2017-08-02
=================

* Fix in organization / group form image URL field (#3661)
* Fix activity test to use utcnow (#3644)
* Changed required permission from 'update' to 'manage_group' (#3631)
* Catch invalid sort param exception (#3630)
* Choose direction of recreated package relationship depending on its type (#3626)
* Fix render_datetime for dates before year 1900 (#3611)
* Fix KeyError in 'package_create' (#3027)
* Allow slug preview to work with autocomplete fields (#2501)
* Fix filter results button not working for organization/group (#3620)
* Allow underscores in URL slug preview on create dataset (#3612)
* Create new resource view if resource format changed (#3515)
* Fixed incorrect escaping in `mail_to` and datapusher's log
* Autocomplete fields are more responsive - 300ms timeout instead of 1s (#3693)
* Fixed dataset count display for groups (#3711)
* Restrict access to form pages (#3684)

v2.5.5 2017-03-22
=================

* Use fully qualified urls for reset emails (#3486)
* Fix edit_resource for resource with draft state (#3480)
* Tag fix for group/organization pages (#3460)
* Setting of datastore_active flag moved to separate function (#3481)

v2.5.4 2017-02-22
=================

 * Fix DataPusher being fired multiple times (#3245)
 * Use the url_for() helper for datapusher URLs (#2866)
 * Resource creation date use datetime.utcnow() (#3447)
 * Fix locale error when using fix ckan.root_path
 * `render_markdown` breaks links with ampersands
 * Check group name and id during package creation
 * Use utcnow() on dashboard_mark_activities_old (#3373)
 * Fix encoding error on DataStore exception
 * Datastore doesn't add site_url to resource created via API (#3189)
 * Fix memberships after user deletion (#3265)
 * Remove idle database connection (#3260)
 * Fix package_owner_org_update action when called via the API (#2661)

v2.5.3 2016-11-02
=================

 * DataPusher called multiple times when creating a dataset (#2856)
 * Default view is re-added when removed before DataStore upload is complete (#3011)
 * "Data API" button disappears on resource page after empty update (#3012)
 * Uncaught email exceptions on user invite (#3077)
 * Resource view description is not rendered as Markdown (#3128)
 * Fix broken html5lib dependency (#3180)
 * ZH_cn translation formatter fix (#3238)
 * Incorrect i18n-paths in extension's setup.cfg (#3275)
 * Changing your user name produces an error and logs you out (#2394)
 * Fix "Load more" functionality in the dashboard (#2346)
 * Fix filters not working when embedding a resource view (#2657)
 * Proper sanitation of header name on SlickGrid view (#2923)
 * Fix unicode error when indexing field of type JSON (#2969)
 * Fix group feeds returning no datasets (#2955)
 * Replace MapQuest tiles in Recline with Stamen Terrain (#3162)
 * Fix bulk operations not taking effect (#3199)
 * Raise validation errors on group/org_member_create (#3108)
 * Incorrect warnings when ckan.views.default_views is empty (#3093)
 * Don't show deleted users/datasets on member_list (#3078)

v2.5.2 2016-03-31
=================

Bug fixes:
 * Avoid submitting resources to the DataPusher multiple times (#2856)
 * Use `resource.url` as raw_resource_url (#2873)
 * Fix DomainObject.count() to return count (#2919)
 * Prevent unicode/ascii conversion errors in DataStore
 * Fix datastore_delete erasing the db when filters is blank (#2885)
 * Avoid package_search exception when using use_default_schema (#2848)
 * Encode EXPLAIN SQL before sending to datastore
 * Use `ckan.site_url` to generate urls of resources (#2592)
 * Fixed the url for the organization_item template

v2.5.1 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version does not require a Solr schema upgrade

Major:
 * CKAN extension language translations integrated using ITranslations interface (#2461, #2643)
 * Speed improvements for displaying a dataset (#2234), home page (#2554), searching (#2382, #2724) and API actions: package_show (#1078) and user_list (#2752).
 * An interface to replace the file uploader, allowing integration with other cloud storage providers (IUploader interface) (#2510)

Minor:
 * package_purge API action added (#1572)
 * revision_list API action now has paging (#1431)
 * Official Ubuntu 14.04 LTS support (#1651)
 * Require/validate current password before allowing a password change (#1940)
 * recline_map_view now recognizes GeoJSON fileds (#2387)
 * Timezone setting (#2494)
 * Updating a resource via upload now saves the last_modified value in the resource (#2519)
 * DataPusher can be customized using the new IDataPusher interface (#2571)
 * Exporting and importing users, with their passwords (if sysadmin) (#2647)

Bug fixes:
 * Fix to allow uppercase letters in local part of email when sending user invitations (#2415)
 * License pick-list changes would cause old values in datasets to be overwritten when edited (#2472)
 * Schema was being passed to package_create_default_resource_views (#2484)
 * Arabic translation format string issue (#2493)
 * Error when deleting organizations (#2512)
 * When DataPusher had an error storing a resource in Data Store, the resource data page gave an error (#2518)
 * Data preview failed when it comes from a server that gives 403 error from a HEAD request (#2530)
 * 'paster views create' failed for non-default dataset types (#2532)
 * DataPusher didn't work for TSV files (#2553)
 * DataPusher failed sometimes due to 'type mismatch' (#2581)
 * IGroupForm wasn't allowing new groups (of type 'group') to use group_form (#2617, #2640)
 * group_purge left behind a Member if it has a parent group/org (#2631)
 * organization_purge left orphaned datasets still with owner_id (#2632)
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks

Changes and deprecations
------------------------

* The old RDF templates to output a dataset in RDF/XML or N3 format have been
  removed. These can be now enabled using the ``dcat`` plugin on *ckanext-dcat*:

    https://github.com/ckan/ckanext-dcat#rdf-dcat-endpoints

* The library used to render markdown has been changed to python-markdown. This
  introduces both ``python-markdown`` and ``bleach`` as dependencies, as ``bleach``
  is used to clean any HTML provided to the markdown processor.

* This is the last version of CKAN to support Postgresql 8.x, 9.0 and 9.1. The
  next minor version of CKAN will require Postgresql 9.2 or later.


v2.5.0 2015-12-17
=================

Cancelled release

v2.4.9 2017-09-27
=================

* Allow overriding email headers (#3781)
* Support non-root instances on fanstatic (#3618)
* Add missing close button on organization page (#3814)

v2.4.8 2017-08-02
=================

* Fix in organization / group form image URL field (#3661)
* Fix activity test to use utcnow (#3644)
* Changed required permission from 'update' to 'manage_group' (#3631)
* Catch invalid sort param exception (#3630)
* Choose direction of recreated package relationship depending on its type (#3626)
* Fix render_datetime for dates before year 1900 (#3611)
* Fix KeyError in 'package_create' (#3027)
* Allow slug preview to work with autocomplete fields (#2501)
* Fix filter results button not working for organization/group (#3620)
* Allow underscores in URL slug preview on create dataset (#3612)
* Create new resource view if resource format changed (#3515)
* Fixed incorrect escaping in `mail_to`
* Autocomplete fields are more responsive - 300ms timeout instead of 1s (#3693)
* Fixed dataset count display for groups (#3711)
* Restrict access to form pages (#3684)

v2.4.7 2017-03-22
=================

* Use fully qualified urls for reset emails (#3486)
* Fix edit_resource for resource with draft state (#3480)
* Tag fix for group/organization pages (#3460)
* Fix for package_search context (#3489)

v2.4.6 2017-02-22
=================

 * Use the url_for() helper for datapusher URLs (#2866)
 * Resource creation date use datetime.utcnow() (#3447)
 * Fix locale error when using fix ckan.root_path
 * `render_markdown` breaks links with ampersands
 * Check group name and id during package creation
 * Use utcnow() on dashboard_mark_activities_old (#3373)
 * Fix encoding error on DataStore exception
 * Datastore doesn't add site_url to resource created via API (#3189)
 * Fix memberships after user deletion (#3265)
 * Remove idle database connection (#3260)
 * Fix package_owner_org_update action when called via the API (#2661)

v2.4.5 2017-02-22
=================

Cancelled release

v2.4.4 2016-11-02
=================

 * Changing your user name produces an error and logs you out (#2394)
 * Fix "Load more" functionality in the dashboard (#2346)
 * Fix filters not working when embedding a resource view (#2657)
 * Proper sanitation of header name on SlickGrid view (#2923)
 * Fix unicode error when indexing field of type JSON (#2969)
 * Fix group feeds returning no datasets (#2955)
 * Replace MapQuest tiles in Recline with Stamen Terrain (#3162)
 * Fix bulk operations not taking effect (#3199)
 * Raise validation errors on group/org_member_create (#3108)
 * Incorrect warnings when ckan.views.default_views is empty (#3093)
 * Don't show deleted users/datasets on member_list (#3078)

v2.4.3 2016-03-31
=================

Bug fixes:
 * Use `resource.url` as raw_resource_url (#2873)
 * Fix DomainObject.count() to return count (#2919)
 * Add offset param to organization_activity (#2640)
 * Prevent unicode/ascii conversion errors in DataStore
 * Fix datastore_delete erasing the db when filters is blank (#2885)
 * Avoid package_search exception when using use_default_schema (#2848)
 * resource_edit incorrectly setting action to new instead of edit
 * Encode EXPLAIN SQL before sending to datastore
 * Use `ckan.site_url` to generate urls of resources (#2592)
 * Don't hide actual exception on paster commands

v2.4.2 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Bug fixes:
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks


v2.4.1 2015-09-02
=================

Note: #2554 fixes a regression where ``group_list`` and ``organization_list``
      where returning extra additional fields by default, causing performance
      issues. This is now fixed, so the output for these actions no longer returns
      ``users``, ``extras``, etc.
      Also, on the homepage template the ``c.groups`` and ``c.group_package_stuff``
      context variables are no longer available.


Bug fixes:

* Fix dataset count in templates and show datasets on featured org/group (#2557)
* Fix autodetect for TSV resources (#2553)
* Improve character escaping in DataStore parameters
* Fix "paster db init" when celery is configured with a non-database backend
* Fix severe performance issues with groups and orgs listings (#2554)


v2.4.0 2015-07-22
=================

Note: This version requires a database upgrade

Note: This version requires a Solr schema upgrade

Major:
 * CKAN config can now be set from environment variables and via the API (#2429)

Minor:
 * API calls now faster: ``group_show``, ``organization_show``, ``user_show``,
   ``package_show``, ``vocabulary_show`` & ``tag_show`` (#1886, #2206, #2207,
   #2376)
 * Require/validate current password before allowing a password change (#1940)
 * Added ``organization_autocomplete`` action (#2125)
 * Default authorization no longer allows anyone to create datasets etc (#2164)
 * ``organization_list_for_user`` now returns organizations in hierarchy if they
   exist for roles set in ``ckan.auth.roles_that_cascade_to_sub_groups`` (#2199)
 * Improved accessibility (text based browsers) focused on the page header
   (#2258)
 * Improved IGroupForm for better customizing groups and organization behaviour
   (#2354)
 * Admin page can now be extended to have new tabs (#2351)


Bug fixes:
 * Command line ``paster user`` failed for non-ascii characters (#1244)
 * Memory leak fixed in datastore API (#1847)
 * Modifying resource didn't update it's last updated timestamp (#1874)
 * Datastore didn't update if you uploaded a new file of the same name as the
   existing file (#2147)
 * Files with really long file were skipped by datapusher (#2057)
 * Multi-lingual Solr schema is now updated so it works again (#2161)
 * Resource views didn't display when embedded in another site (#2238)
 * ``resource_update`` failed if you supplied a revision_id (#2340)
 * Recline could not plot GeoJSON on a map (#2387)
 * Dataset create form 404 error if you added a resource but left it blank (#2392)
 * Editing a resource view for a file that was UTF-8 and had a BOM gave an
   error (#2401)
 * Email invites had the email address changed to lower-case (#2415)
 * Default resource views not created when using a custom dataset schema (#2421,
   #2482)
 * If the licenses pick-list was customized to remove some, datasets with old
   values had them overwritten when edited (#2472)
 * Recline views failed on some non-ascii characters (#2490)
 * Resource proxy failed if HEAD responds with 403 (#2530)
 * Resource views for non-default dataset types couldn't be created (#2532)

Changes and deprecations
------------------------

* The default of allowing anyone to create datasets, groups and organizations
  has been changed to False. It is advised to ensure you set all of the
  :ref:`config-authorization` options explicitly in your CKAN config. (#2164)

* The ``package_show`` API call does not return the ``tracking_summary``,
  keys in the dataset or resources by default any more.

  Any custom templates or users of this API call that use these values will
  need to pass: ``include_tracking=True``.

* The legacy `tests` directory has moved to `tests/legacy`, the
  `new_tests` directory has moved to `tests` and the `new_authz.py`
  module has been renamed `authz.py`. Code that imports names from the
  old locations will continue to work in this release but will issue
  a deprecation warning. (#1753)

* ``group_show`` and ``organization_show`` API calls no longer return the
  datasets by default (#2206)

  Custom templates or users of this API call will need to pass
  ``include_datasets=True`` to include datasets in the response.

* The ``vocabulary_show`` and ``tag_show`` API calls no longer returns the
  ``packages`` key - i.e. datasets that use the vocabulary or tag.
  However ``tag_show`` now has an ``include_datasets`` option. (#1886)

* Config option ``site_url`` is now required - CKAN will not abort during
  start-up if it is not set. (#1976)

v2.3.5 2016-11-02
=================

 * Fix "Load more" functionality in the dashboard (#2346)
 * Fix filters not working when embedding a resource view (#2657)
 * Proper sanitation of header name on SlickGrid view (#2923)
 * Fix unicode error when indexing field of type JSON (#2969)
 * Fix group feeds returning no datasets (#2955)
 * Replace MapQuest tiles in Recline with Stamen Terrain (#3162)
 * Fix bulk operations not taking effect (#3199)
 * Raise validation errors on group/org_member_create (#3108)
 * Incorrect warnings when ckan.views.default_views is empty (#3093)
 * Don't show deleted users/datasets on member_list (#3078)

v2.3.4 2016-03-31
=================

Bug fixes:
 * Use `resource.url` as raw_resource_url (#2873)
 * Fix DomainObject.count() to return count (#2919)
 * Prevent unicode/ascii conversion errors in DataStore
 * Fix datastore_delete erasing the db when filters is blank (#2885)
 * Avoid package_search exception when using use_default_schema (#2848)
 * resource_edit incorrectly setting action to new instead of edit
 * Use `ckan.site_url` to generate urls of resources (#2592)
 * Don't hide actual exception on paster commands

v2.3.3 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Bug fixes:
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks


v2.3.2 2015-09-02
=================

Bug fixes:
* Fix autodetect for TSV resources (#2553)
* Improve character escaping in DataStore parameters
* Fix "paster db init" when celery is configured with a non-database backend


v2.3.1 2015-07-22
=================

Bug fixes:
 * Resource views won't display when embedded in another site (#2238)
 * ``resource_update`` failed if you supplied a revision_id (#2340)
 * Recline could not plot GeoJSON on a map (#2387)
 * Dataset create form 404 error if you added a resource but left it blank (#2392)
 * Editing a resource view for a file that was UTF-8 and had a BOM gave an
   error (#2401)
 * Email invites had the email address changed to lower-case (#2415)
 * Default resource views not created when using a custom dataset schema (#2421,
   #2482)
 * If the licenses pick-list was customized to remove some, datasets with old
   values had them overwritten when edited (#2472)
 * Recline views failed on some non-ascii characters (#2490)
 * Resource views for non-default dataset types couldn't be created (#2532)


v2.3 2015-03-04
===============

Note: This version requires a requirements upgrade on source installations

Note: This version requires a database upgrade

Note: This version requires a Solr schema upgrade

Note: This version requires a DataPusher upgrade on source installations. You
    should target DataPusher=>0.0.6 and upgrade its dependencies.


Major:
 * Completely refactored resource data visualizations, allowing multiple
   persistent views of the same data an interface to manage and configure
   them. (#1251, #1851, #1852, #2204, #2205) Check the updated documentation
   to know more, and the "Changes and deprecations" section for migration
   details:

     http://docs.ckan.org/en/latest/maintaining/data-viewer.html

 * Responsive design for the default theme, that allows nicer rendering across
   different devices (#1935)
 * Improved DataStore filtering and full text search capabilities (#1792, #1830, #1838, #1815)
 * Added new extension points to modify the DataStore behaviour (#1725)
 * Simplified two-step dataset creation process (#1659)
 * Ability for users to regenerate their own API keys (#1412)
 * New ``package_patch`` action to allow individual fields dataset updates
   (#1416, #1679)
 * Changes on the authentication mechanism to allow more secure setups (``httponly``
   and ``secure`` cookies, disable CORS, etc). (#2004. #2050, #2052
   ...) See "Changes and deprecations" section for more details and
   "Troubleshooting" for migration instructions.
 * Better support for custom dataset types (#1795, #2083)
 * Extensions can combine free-form extras and ``convert_to_extras`` fields (#1894)
 * Updated documentation theme, now clearer and responsive (#1845)


Minor:
 * Adding custom fields tutorial (#790)
 * Add metadata created and modified fields to the dataset page (#655)
 * Improve IFacets plugin interface docstrings (#781)
 * Remove help string from API calls (#1318)
 * Add "datapusher submit" command to upload existing resources data (#1792)
 * More template blocks to allow for easier extension maintenance (#1301)
 * CKAN API - remove help string from standard calls (#1318)
 * Hide activity by selected users on activity stream (#1330)
 * Documentation and clarification about "CKAN Flavored Markdown" (#1332)
 * Resource formats are now guessed automatically (#1350)
 * New JavaScript modules tutorial (#1377)
 * Allow overriding dataset, group, org validation (#1400)
 * Remove ResourceGroups, show package_id on resources (#1407)
 * Better errors for NAVL junk (#1418)
 * DataPusher integration improvements (#1446)
 * Allow people to create unowned datasets when they belong to an org (#1473)
 * Add res_type to Solr schema (#1495)
 * Separate data and metadata licenses on create dataset page (#1503)
 * Allow CKAN (and paster) to find config from envvar (#1597)
 * Added xlsx and tsv to the defaults for ckan.datapusher.formats. (#1644)
 * Add resource extras to Solr search index (#1709)
 * Prevent packages update in organization_update (#1711)
 * Programatically log user in after registration (#1721)
 * New plugin interfaces: IValidators.get_validators and IConverters.get_converters (#1841)
 * Index resource name in Solr (#1905)
 * Update search index after membership changes (#1917)
 * resource_show: use package_show to get validated data (#1921)
 * Serve placeholder images locally (#1951)
 * Don't get all datasets when loading the org in the dataset page (#1978)
 * Text file preview - lack of vertical scroll bar for long files (#1982)
 * Changes to allow better use of custom group types in IGroupForm extensions (#1987)
 * Remove moderated edits (#2006)
 * package_create: allow sysadmins to set package ids (#2102)
 * Enable a logged in user to move dataset to another organization (#2218)
 * Move PDF views into a separate extension (#2270)
 * Do not provide email configuration in default config file (#2273)
 * Add custom DataStore SQLAlchemy properties (#2279)


Bug fixes:
 * Set up stats extension as namespace plugin (#291)
 * Fix visibility validator for datasets (#1188)
 * Select boxes with autocomplete are clearing their placeholders (#1278)
 * Default search ordering on organization home page is broken (#1368)
 * related_list logic function throws a 503 without any parameters (#1384)
 * Exception on group dictize due to 'with_capacity' on context (#1390)
 * Wrong template on Add member page (#1392)
 * Overflowing email address on user page (#1398)
 * The reset password e-mail is using an incorrect translation string (#1409)
 * You can't view a group when there is an IGroupForm (#1420)
 * Disabling activity_streams borks editing groups and user (#1421)
 * Use a more secure default for the repoze secret key (#1422)
 * Duplicated Required Fields notice on Group form (#1426)
 * UI language reset after account creation (#1429)
 * num_followers and package_count not in default_group_schema (#1434)
 * Fix extras deletion (#1449)
 * Fix resource reordering (#1450)
 * Datastore callback fails when browser url is different from site_url (#1451)
 * sysadmins should not create datasets wihout org when config is set (#1453)
 * Member Editing Fixes (#1454)
 * Bulk editing broken on IE7 (#1455)
 * Fix group deletion on IE7 (#1460)
 * Organization ATOM feed is broken (#1463)
 * Users can not delete a dataset that not belongs to an organization (#1471)
 * Error during authorization in datapusher_hook (#1487)
 * Wrong datapusher hook callback URL on non-root deployments (#1490)
 * Wrong breadcrumbs on new dataset form and resource pages (#1491)
 * Atom feed Content-Type returned as 'text/html' (#1504)
 * Invite to organization causes Internal Server error (#1505)
 * Dataset tags autocomplete doesn't work (#1512)
 * Activity Stream from: Organization Error group not found (#1519)
 * Improve password hashing algorithm (#1530)
 * Can't download resources with geojson extension (#1534)
 * All datasets for featured group/organization shown on home page  (#1569)
 * Able to list private datasets via the API (#1580)
 * Don't lowercase the names of uploaded files (#1584)
 * Show more facets only if there are more facts to show (#1612)
 * resource_create should break when called without URL (#1641)
 * Creating a DataStore resource with the package_id fails for a normal user (#1652)
 * Fix package permission checks for create+update (#1664)
 * bulk_process page for non-existent organization throws Exception (#1682)
 * Catch NotFound error in resource_proxy (#1684)
 * Fix int_validator (#1692)
 * Current date indexed on empty "_date" fields (#1701)
 * Possible to show a resource inside an arbitary dataset (#1707)
 * Edit member page shows wrong fields (#1723)
 * Insecure content warning when running Recline under SSL (#1729)
 * Flash messages not displayed as part of page.html (#1743)
 * package_show response includes solr rubbish when using ckan.cache_validated_datasets (#1764)
 * "Add some resources" link shown to unauthorized users (#1766)
 * email notifications via paster plugin post erroneously demands authentication (#1767)
 * Inserting empty arrays in JSON type fields in datastore fails (#1776)
 * Ordering a dataset listing loses the existing filters (#1791)
 * Don't delete all cookies whose names start with "ckan" (#1793)
 * Upgrade some major requirements (eg SQLAlchemy, Requests) (#1817, #1819)
 * list of member roles disappears on add member page (#1873)
 * Stats plugin should only show active datasets (#1936)
 * Featured group on homepage not linking to group (#1996)
 * --reload doesn't work on the 'paster serve' command (#2013)
 * Can not override auth config options from tests (#2035)
 * Fix ``resource_create`` authorization (#2037)
 * package_search gives internal server error if page < 1 (#2042)
 * Fix organization pagination (#2141)
 * Resource extras can not be updated (#2158)
 * package_show doesn't validate when a custom schema is used (#2175)
 * Update jQuery minified version to match the unminified one (#1750)
 * Fix exception during database upgrade (#2029)
 * Fix resources disappearing on dataset upate (#1779)
 * Fix activity stream queries performance on large instances (#2008)
 * Only link to http, https and ftp resource urls (#2085)
 * Avoid private and deleted datasets on stats plugin (#1936)
 * Fix tags count and group links in stats extension (#1649)
 * Make resource_create auth work against package_update (#2037)
 * Fix DataStore permissions check on startup (#1374)
 * Fix datastore docs link (#2044)
 * Clean up field names before rendering the Recline table (#2319)
 * Don't "normalize" resource URL in recline view (#2324)
 * Don't assume resource format is there on text preview (#2320)
 * And many, many more!

Changes and deprecations
------------------------

* By convention, view plugin names now end with ``_view`` rather than
  ``_preview`` (eg ``recline_view`` rather than ``recline_preview``). You will
  need to update them on the :ref:`ckan.plugins` setting.

* The way resource visualizations are created by default has changed. You might
  need to set the :ref:`ckan.views.default_views` configuration option and run
  a migration command on existing instances. Please refer to the migration
  guide for more details:

    http://docs.ckan.org/en/latest/maintaining/data-viewer.html#migrating-from-previous-ckan-versions

* The PDF Viewer extension has been moved to a separate extension:
  https://github.com/ckan/ckanext-pdfview. Please install it separately if
  you are using the ``pdf_view`` plugin (or the old ``pdf_preview`` one).

* The action API (v3) no longer returns the full help for the action on each
  request. It rather includes a link to a separate call to get the action
  help string.

* The ``user_show`` API call does not return the ``datasets``,
  ``num_followers`` or ``activity`` keys by default any more.

  Any custom templates or users of this API call that use these values will
  need to specify parameters: ``include_datasets`` or
  ``include_num_followers``.

  ``activity`` has been removed completely as it was actually a list of
  revisions, rather than the activity stream. If you want the actual activity
  stream for a user, call ``user_activity_list`` instead.

* The output of ``resource_show`` now contains a ``package_id`` key that links
  to the parent dataset.

* ``helpers.get_action()`` (or ``h.get_action()`` in templates) is deprecated.

  Since action functions raise exceptions and templates cannot catch
  exceptions, it's not a good idea to call action functions from templates.

  Instead, have your controller method call the action function and pass the
  result to your template using the ``extra_vars`` param of ``render()``.

  Alternatively you can wrap individual action functions in custom template
  helper functions that handle any exceptions appropriately, but this is likely
  to make your the logic in your templates more complex and templates are
  difficult to test and debug.

  Note that logic.get_action() and toolkit.get_action() are *not* deprecated,
  core code and plugin code should still use ``get_action()``.

* Cross-Origin Resource Sharing (CORS) support is no longer enabled by
  default. Previously, Access-Control-Allow-* response headers were added for
  all requests, with Access-Control-Allow-Origin set to the wildcard value
  ``*``. To re-enable CORS, use the new ``ckan.cors`` configuration settings
  (:ref:`ckan.cors.origin_allow_all` and :ref:`ckan.cors.origin_whitelist`).

* The HttpOnly flag will be set on the authorization cookie by default. For
  enhanced security, we recommend using the HttpOnly flag, but this behaviour
  can be changed in the ``Repoze.who`` settings detailed in the Config File
  Options documentation (:ref:`who.httponly`).

* The OpenID login option has been removed and is no longer supported. See
  "Troubleshooting" if you are upgrading an existing CKAN instance as you may
  need to update your ``who.ini`` file.

Template changes
----------------

* Note to people with custom themes: If you've changed the
  ``{% block secondary_content %}`` in templates/package/search.html pay close
  attention as this pull request changes the structure of that template block a
  little.

  Also: There's a few more bootstrap classes (especially for grid layout) that
  are now going to be in the templates. Take a look if any of the following
  changes might effect your content blocks:

  https://github.com/ckan/ckan/pull/1935

Troubleshooting:
----------------

* Login does not work, for existing and new users.

  You need to update your existing ``who.ini`` file.

  - In the ``[plugin:auth_tkt]`` section, replace::

      use = ckan.config.middleware:ckan_auth_tkt_make_app

    with::

      use = ckan.lib.auth_tkt:make_plugin

  - In ``[authenticators]``, add the ``auth_tkt`` plugin

  Also see the next point for OpenID related changes.

* Exception on first load after upgrading from a previous CKAN version::

    ImportError: <module 'ckan.lib.authenticator' from '/usr/lib/ckan/default/src/ckan/ckan/lib/authenticator.py'> has no 'OpenIDAuthenticator' attribute

  or::

    ImportError: No module named openid

  There are OpenID related configuration options in your ``who.ini`` file which
  are no longer supported.

  This file is generally located in ``/etc/ckan/default/who.ini`` but its location
  may vary if you used a custom deployment.

  The options that you need to remove are:

  - The whole ``[plugin:openid]`` section
  - In ``[general]``, replace::

       challenge_decider = repoze.who.plugins.openid.classifiers:openid_challenge_decider

    with::

       challenge_decider = repoze.who.classifiers:default_challenge_decider

  - In ``[identifiers]``, remove ``openid``
  - In ``[authenticators]``, remove ``ckan.lib.authenticator:OpenIDAuthenticator``
  - In ``[challengers]``, remove ``openid``

  This is a diff with the whole changes:

   https://github.com/ckan/ckan/pull/2058/files#diff-2

  Also see the previous point for other ``who.ini`` changes.

v2.2.4 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Bug fixes:
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks

v2.2.3 2015-07-22
=================

Bug fixes:
 * Allow uppercase emails on user invites (#2415)
 * Fix broken boolean validator (#2443)
 * Fix auth check in resources_list.html (#2037)
 * Key error on resource proxy (#2425)
 * Ignore revision_id passed to resources (#2340)
 * Add reset for reset_key on successful password change (#2379)

v2.2.2 2015-03-04
=================

Bug fixes:
 * Update jQuery minified version to match the unminified one (#1750)
 * Fix exception during database upgrade (#2029)
 * Fix resources disappearing on dataset upate (#1779)
 * Fix activity stream queries performance on large instances (#2008)
 * Only link to http, https and ftp resource urls (#2085)
 * Avoid private and deleted datasets on stats plugin (#1936)
 * Fix tags count and group links in stats extension (#1649)
 * Make resource_create auth work against package_update (#2037)
 * Fix DataStore permissions check on startup (#1374)
 * Fix datastore docs link (#2044)
 * Fix resource extras getting lost on resource update (#2158)
 * Clean up field names before rendering the Recline table (#2319)
 * Don't "normalize" resource URL in recline view (#2324)
 * Don't assume resource format is there on text preview (#2320)

v2.2.1 2014-10-15
=================

Bug fixes:
 * Organization image_url is not displayed in the dataset view. (#1934)
 * list of member roles disappears on add member page if you enter a user that doesn't exist  (#1873)
 * group/organization_member_create do not return a value. (#1878)
 * i18n: Close a tag in French translation in Markdown syntax link (#1919)
 * organization_list_for_user() fixes (#1918)
 * Don't show private datasets to group members (#1902)
 * Incorrect link in Organization snippet on dataset page (#1882)
 * Prevent reading system tables on DataStore SQL search (#1871)
 * Ensure that the DataStore is running on legacy mode when using PostgreSQL < 9.x (#1879)
 * Select2 in the Tags field is broken(#1864)
 * Edit user encoding error (#1436)
 * Able to list private datasets via the API (#1580)
 * Insecure content warning when running Recline under SSL (#1729)
 * Add quotes to package ID in Solr query in _bulk_update_dataset to prevent Solr errors with custom dataset IDs. (#1853)
 * Ordering a dataset listing loses the existing filters (#1791)
 * Inserting empty arrays in JSON type fields in datastore fails (#1776)
 * email notifications via paster plugin post erroneously demands authentication (#1767)
 * "Add some resources" link shown to unauthorized users (#1766)
 * Current date indexed on empty "\*_date" fields (#1701)
 * Edit member page shows wrong fields (#1723)
 * programatically log user in after registration (#1721)
 * Dataset tags autocomplete doesn't work (#1512)
 * Deleted Users bug (#1668)
 * UX problem with previous and next during dataset creation (#1598)
 * Catch NotFound error in resources page (#1685)
 * _tracking page should only respond to POST (#1683)
 * bulk_process page for non-existent organization throws Exception (#1682)
 * Fix package permission checks for create+update (#1664)
 * Creating a DataStore resource with the package_id fails for a normal user (#1652)
 * Trailing whitespace in resource URLs not stripped (#1634)
 * Move the closing div inside the block (#1620)
 * Fix open redirect (#1419)
 * Show more facets only if there are more facts to show (#1612)
 * Fix breakage in package groups page (#1594)
 * Fix broken links in RSS feed (#1589)
 * Activity Stream from: Organization Error group not found (#1519)
 * DataPusher and harvester collision (#1500)
 * Can't download resources with geojson extension (#1534)
 * Oversized Forgot Password button and field (#1508)
 * Invite to organization causes Internal Server error (#1505)


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

v2.1.6 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Bug fixes:
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks

v2.1.5 2015-07-22
=================

Bug fixes:
 * Fix broken boolean validator (#2443)
 * Key error on resource proxy (#2425)
 * Ignore revision_id passed to resources (#2340)
 * Add reset for reset_key on successful password change (#2379)

v2.1.4 2015-03-04
=================

Bug fixes:
 * Only link to http, https and ftp resource urls (#2085)
 * Avoid private and deleted datasets on stats plugin (#1936)
 * Fix tags count and group links in stats extension (#1649)
 * Make resource_create auth work against package_update (#2037)
 * Fix DataStore permissions check on startup (#1374)
 * Fix datastore docs link (#2044)
 * Fix resource extras getting lost on resource update (#2158)
 * Clean up field names before rendering the Recline table (#2319)
 * Don't "normalize" resource URL in recline view (#2324)
 * Don't assume resource format is there on text preview (#2320)

v2.1.3 2014-10-15
=================

Bug fixes:
 * Organization image_url is not displayed in the dataset view. (#1934)
 * i18n: Close a tag in French translation in Markdown syntax link (#1919)
 * organization_list_for_user() fixes (#1918)
 * Incorrect link in Organization snippet on dataset page (#1882)
 * Prevent reading system tables on DataStore SQL search (#1871)
 * Ensure that the DataStore is running on legacy mode when using PostgreSQL < 9.x (#1879)
 * Edit user encoding error (#1436)
 * Able to list private datasets via the API (#1580)
 * Insecure content warning when running Recline under SSL (#1729)
 * Add quotes to package ID in Solr query in _bulk_update_dataset to prevent Solr errors with custom dataset IDs. (#1853)
 * Ordering a dataset listing loses the existing filters (#1791)
 * Inserting empty arrays in JSON type fields in datastore fails (#1776)
 * programatically log user in after registration (#1721)
 * Deleted Users bug (#1668)
 * Catch NotFound error in resources page (#1685)
 * bulk_process page for non-existent organization throws Exception (#1682)
 * Default search ordering on organization home page is broken (#1368)
 * Term translations of organizations (#1274)
 * Preview fails on private datastore resources (#1221)
 * Strip whitespace from title in model dictize (#1228)

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

v2.0.8 2015-12-17
=================

Note: This version requires a requirements upgrade on source installations

Bug fixes:
 * Fix Markdown rendering issue
 * Return default error page on fanstatic errors
 * Prevent authentication when using API callbacks

v2.0.7 2015-07-22
=================

Bug fixes:
 * Fix broken boolean validator (#2443)
 * Key error on resource proxy (#2425)
 * Ignore revision_id passed to resources (#2340)
 * Add reset for reset_key on successful password change (#2379)

v2.0.6 2015-03-04
=================

Bug fixes:
 * Only link to http, https and ftp resource urls (#2085)
 * Avoid private and deleted datasets on stats plugin (#1936)
 * Fix tags count and group links in stats extension (#1649)
 * Make resource_create auth work against package_update (#2037)
 * Fix datastore docs link (#2044)
 * Fix resource extras getting lost on resource update (#2158)
 * Clean up field names before rendering the Recline table (#2319)
 * Don't "normalize" resource URL in recline view (#2324)
 * Don't assume resource format is there on text preview (#2320)

v2.0.5 2014-10-15
=================

Bug fixes:
 * organization_list_for_user() fixes (#1918)
 * Incorrect link in Organization snippet on dataset page (#1882)
 * Prevent reading system tables on DataStore SQL search (#1871)
 * Ensure that the DataStore is running on legacy mode when using PostgreSQL < 9.x (#1879)
 * Current date indexed on empty "\*_date" fields (#1701)
 * Able to list private datasets via the API (#1580)
 * Insecure content warning when running Recline under SSL (#1729)
 * Inserting empty arrays in JSON type fields in datastore fails (#1776)
 * Deleted Users bug (#1668)

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

Organizations based authorization (see :doc:`/maintaining/authorization`):
 CKAN's new "organizations" feature replaces the old authorization system
 with a new one based on publisher organizations. It replaces the "Publisher
 Profile and Workflow" feature from CKAN 1.X, any instances relying on it will
 need to be updated.

 * New organization-based authorization and organization of datasets
 * Supports private datasets
 * Publisher workflow
 * New authorization ini file options


New frontend (see :doc:`/theming/index`):
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
   https://travis-ci.org/ckan/ckan/
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
  * Explicit User object and improved user account UI with recent edits etc (#111, #66, #67)
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
