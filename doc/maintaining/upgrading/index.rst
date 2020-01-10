==============
Upgrading CKAN
==============

This document describes the different types of CKAN release, and explains
how to upgrade a site to a newer version of CKAN.

.. seealso::

   :doc:`/changelog`
     The changelog lists all CKAN releases and the main changes introduced in
     each release.

   :doc:`/contributing/release-process`
     Documentation of the process that the CKAN developers follow to do a
     CKAN release.


.. _releases:

-------------
CKAN releases
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
 Minor releases, such as CKAN 1.8 and CKAN 2.1, increment the minor version
 number. These releases are not as disruptive as major releases, but
 backwards-incompatible changes *may* be introduced in minor releases. The
 :doc:`/changelog` will document any breaking changes. We aim to release a minor
 version of CKAN roughly every three months.

Patch Releases
  Patch releases, such as CKAN 1.8.1 or CKAN 2.0.1, increment the patch version
  number. These releases do not break backwards-compatibility, they include
  only bug fixes and security fixes, ensured to be non-breaking.
  Patch releases do not contain:

  - Database schema changes or migrations
  - Function interface changes
  - Plugin interface changes
  - New dependencies (unless absolutely necessary)
  - Big refactorings or new features in critical parts of the code

.. note::

   Users should always run the latest patch release for the minor release they
   are on, as patch releases contain important bug fixes and security updates.
   Because patch releases don't include backwards incompatible changes, the
   upgrade process (as described in :doc:`upgrade-package-to-patch-release`)
   should be straightforward.

   Outdated patch releases will no longer be supported after a newer patch
   release has been released. For example once CKAN 2.0.2 has been released,
   CKAN 2.0.1 will no longer be supported.

Releases are announced on the
`ckan-announce mailing list <http://lists.okfn.org/mailman/listinfo/ckan-announce>`_,
a low-volume list that CKAN instance maintainers can subscribe to in order to
be up to date with upcoming releases.


.. _upgrading:

--------------
Upgrading CKAN
--------------

This section will walk you through the steps to upgrade your CKAN site to a
newer version of CKAN.

.. note::

    Before upgrading your version of CKAN you should check that any custom
    templates or extensions you're using work with the new version of CKAN.
    For example, you could install the new version of CKAN in a new virtual
    environment and use that to test your templates and extensions.

.. note::

    You should also read the :doc:`/changelog` to see if there are any extra
    notes to be aware of when upgrading to the new version.


1. Backup your database
=======================

You should always backup your CKAN database before upgrading CKAN. If something
goes wrong with the CKAN upgrade you can use the backup to restore the database
to its pre-upgrade state.

#. Activate your virtualenv and switch to the ckan source directory, e.g.:

   .. parsed-literal::

    |activate|
    cd |virtualenv|/src/ckan

#. :ref:`Backup your CKAN database <db dumping and loading>`


2. Upgrade CKAN
===============

The process of upgrading CKAN differs depending on whether you have a package
install or a source install of CKAN, and whether you're upgrading to a
:ref:`major, minor or patch release <releases>` of CKAN. Follow the
appropriate one of these documents:

.. toctree::
    :maxdepth: 1

    upgrade-package-ckan-1-to-2
    upgrade-package-to-patch-release
    upgrade-package-to-minor-release
    upgrade-source
    upgrade-postgres
    upgrade-to-python3
