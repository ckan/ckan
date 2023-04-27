
.. _releases:

=============
CKAN releases
=============

This document describes the different types of CKAN releases, and explains which
releases are officially supported at any given time.

.. include:: /_supported_versions.rst

-------------
Release types
-------------

CKAN follows a predictable release cycle so that users can depend on stable
releases of CKAN, and can plan their upgrades to new releases.

Each release has a version number of the form ``M.m`` (eg. 2.1) or ``M.m.p``
(eg. 1.8.2), where ``M`` is the **major version**, ``m`` is the **minor
version** and ``p`` is the **patch version** number. There are three types of
release:

Major Releases
 Major releases, such as CKAN 1.0 and CKAN 2.0, increment the major version
 number.  These releases contain major changes in the CKAN code base, with
 significant refactorings and breaking changes, for instance in the API or the
 templates.  These releases are very infrequent.

Minor Releases
 Minor releases, such as CKAN 2.9 and CKAN 2.10, increment the minor version
 number. These releases are not as disruptive as major releases, but the will
 *may* include some backwards-incompatible changes. The
 :doc:`/changelog` will document any breaking changes. We aim to release a minor
 version of CKAN roughly twice a year.

Patch Releases
  Patch releases, such as CKAN 2.9.5 or CKAN 2.10.1, increment the patch version
  number. These releases do not break backwards-compatibility, they include
  only bug fixes for security and performance issues.
  Patch releases do not contain:

  - Database schema changes or migrations (unless addressing security issues)
  - Solr schema changes
  - Function interface changes
  - Plugin interface changes
  - New dependencies (unless addressing security issues)
  - Big refactorings or new features in critical parts of the code

.. note::


   Outdated patch releases will no longer be supported after a newer patch
   release has been released. For example once CKAN 2.9.2 has been released,
   CKAN 2.9.1 will no longer be supported.

Releases are announced on the
`ckan-announce mailing list <https://groups.google.com/a/ckan.org/g/ckan-announce>`_,
a low-volume list that CKAN instance maintainers can subscribe to in order to
be up to date with upcoming releases.


.. _supported_versions:

------------------
Supported versions
------------------

At any one time, the CKAN Tech Team will support the latest patch release of the last
released minor version plus the last patch release of the previous minor version.

The previous minor version will only receive security and bug fixes. If a patch does not clearly
fit in these categories, it is up to the maintainers to decide if it can be backported to a previous version.

The latest patch releases are the only ones officially supported. Users should always run the
latest patch release for the minor release they are on, as they contain important bug fixes and security updates.
Running CKAN in an unsupported version puts your site and data at risk.

Because patch releases don't include backwards incompatible changes, the
upgrade process (as described in :doc:`upgrading/upgrade-package-to-patch-release`)
should be straightforward.

Extension maintainers can decide at their discretion to support older CKAN versions.


.. seealso::

   :doc:`/changelog`
     The changelog lists all CKAN releases and the main changes introduced in
     each release.

   :doc:`/contributing/release-process`
     Documentation of the process that the CKAN developers follow to do a
     CKAN release.

