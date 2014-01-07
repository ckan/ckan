==============
Upgrading CKAN
==============

This document covers CKAN releases and how to upgrade a site to a newer version
of CKAN:

* :ref:`releases` describes the different types of CKAN release
* :ref:`release process` describes the process that the CKAN dev team follows,
  when we make a new CKAN release
* Finally, :ref:`upgrading` will walk you through the steps for upgrading a
  CKAN site to a newer version of CKAN

For a list of CKAN releases and the changes introduced in each release, see the
:doc:`changelog`.


.. _releases:

-------------
CKAN releases
-------------

CKAN follows a predictable release cycle so that users can depend on stable
releases of CKAN, and can plan their upgrades to new releases.
The :doc:`changelog` documents the main changes in each release.

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
 :doc:`changelog` will document any breaking changes. We aim to release a minor
 version of CKAN roughly every three months.

Patch Releases
  Patch releases, such as CKAN 1.8.1 or CKAN 2.0.1, increment the patch version
  number. These releases do not break backwards-compatibility, they include
  only bug fixes and non-breaking optimizations and features.
  Patch releases do not contain:

  - Database schema changes or migrations
  - Function interface changes
  - Plugin interface changes
  - New dependencies
  - Big refactorings or new features in critical parts of the code

Users should always run the latest patch release for the minor release they
are on, as they contain important bug fixes and security updates. As they
don't include backwards incompatible changes, the upgrade process (as
described in :doc:`upgrade-package-to-patch-release`) should be
straightforward.

Outdated patch releases will no longer be supported after a newer patch
release has been released. For example once CKAN 2.0.2 has been released,
CKAN 2.0.1 will no longer be supported.

Releases are announced on the ``ckan-announce`` mailing list, a low-volume
list that CKAN instance maintainers can subscribe to in order to be up to date
with upcoming releases. You can sign up to the list here:

http://lists.okfn.org/mailman/listinfo/ckan-announce

.. _release process:

---------------
Release process
---------------

.. _beta.ckan.org: http://beta.ckan.org
.. _Transifex: https://www.transifex.com/projects/p/ckan

When the development is ready to start the process of releasing a new version
of CKAN, we will:

#. Create a new release branch from the master branch, named ``release-v*``
   where ``*`` is the release's version number.

#. Deploy the release branch on `beta.ckan.org`_ for testing.

#. During the next two-three weeks, we'll allow changes on the release branch
   only to stabilize the code, update translations and documentation, etc.
   (new features are usually not added on the release branch).

#. During the final week before the release, we'll only allow critical bug
   fixes to be committed on the release branch.

.. _ckan-dev: http://lists.okfn.org/mailman/listinfo/ckan-dev
.. _ckan-discuss: http://lists.okfn.org/mailman/listinfo/ckan-discuss
.. _ckan-announce: http://lists.okfn.org/mailman/listinfo/ckan-announce

At some point during the beta period a **strings freeze** will begin.
That means that no changes to translatable strings are allowed on the release
branch (no new strings, or changes to existing strings). This will give
translators time to update the translations on Transifex_. We'll publish a
**call for translations** to the `ckan-dev`_ and `ckan-discuss`_ mailing
lists, announcing that the new version is ready to be translated.

At some point before the final release, we'll announce an **end of
translations** after which no new translations will be pulled into the release
branch. At this point we'll deploy the translations to `beta.ckan.org`_ and
we'll put out a request for people to test CKAN in their languages.

The upcoming releases are announced on the `ckan-announce`_ mailing list.

Release branches are not merged back into master. All changes on a release
branch are cherry-picked from master (or merged from special branches based on
the release branch).

To ensure that the release guidelines are enforced one of the CKAN core
developers will act as **Release Manager**. They have the final say on what is
merged into the release branches.

Detailed release process instructions for CKAN Developers can be found in the
:doc:`release-process` document:

.. toctree::
   :maxdepth: 1

   release-process


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

    You should also read the :doc:`changelog` to see if there are any extra
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

#. Backup your CKAN database using the ``db dump`` command, for
   example:

   .. parsed-literal::

    paster db dump --config=\ |development.ini| my_ckan_database.pg_dump

   This will create a file called ``my_ckan_database.pg_dump``, you can use the
   the ``db load`` command to restore your database to the state recorded in
   this file. See :ref:`paster db` for details of the ``db dump`` and ``db
   load`` commands.


2. Upgrade CKAN
===============

The process of upgrading CKAN differs depending on whether you have a package
install or a source install of CKAN, and whether you're upgrading to a
:ref:`major, minor or patch release <releases>` of CKAN. Follow the
appropriate one of these documents:

.. toctree::

    upgrade-package-ckan-1-to-2
    upgrade-package-to-patch-release
    upgrade-package-to-minor-release
    upgrade-source
