CKAN Release Cycle
==================

CKAN follows a standardized release process in order to ensure that releases
are stable and backwards compatible, and to allow external developers to
oversee the development process and plan future upgrades.

Release types
-------------

Versions for each release are numbered as *X.Y* or *X.Y.Z*. There are three
types of releases:

* **Major Releases**
    These increment the main version count (eg *2.0*) and
    represent major changes in the CKAN code base, with significant refactorings
    and breaking changes, for instance on the API or the templates. These releases
    are very infrequent, 2.0 will be the first one in CKAN's history.

* **Point Releases**
    These increment the second version number (eg *2.1*) and
    represent stable lines among CKAN releases. Although not as disruptive as on
    major releases, bacwards incompatible changes may be introduced on point
    releases. The CHANGELOG will describe which are these incompatible changes.
    We aim to do a Point release roughly every three months.

* **Point point Releases**
    These increment the third version number (eg *2.1.3*)
    and don't break compatibility. That means for example that an application
    running CKAN 1.8 or 1.8.1 can be safely upgraded to 1.8.2 or 1.8.3. These
    releases are branched from their Point release or from the last Point point
    release if any. They only include bug fixes and non-breaking optimizations or
    small features. They must not include:

  - DB migrations or schema changes
  - Function interface changes
  - Plugin interface changes
  - New dependencies
  - Big refactorings or new features on critical parts of the code


CKAN Release Process Overview
-----------------------------

When the development team thinks master is at a good point to start the
release process a new branch will be created with the name *release-v{version
number}*. This is the beta branch for this release, and it will be deployed to
the beta staging site (http://beta.ckan.org). During the next two-three weeks
changes will be allowed to stabilize the code, update i18n and documentation,
etc. During the last week, only critical bug fixes are allowed.

At some point during the beta process a translation freeze will be put in
place. That means that no changes to the translatable strings are allowed (new
strings or changes on existing ones). This will give time to translators to
update the translations on Transifex_.

Release branches are not merged back into master. All changes must be
cherry-picked from master (or merged from special branches based on the release
branch).

To ensure that the release guidelines are enforced one of the CKAN core
developers will act as Release Manager. He or she has the final say on what is
merged into the release branches.

The actual process followed by CKAN developers can be found in
:doc:`release-process`.


.. _Transifex: https://www.transifex.com/projects/p/ckan
