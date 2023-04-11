
.. _upgrading:

==============
Upgrading CKAN
==============

This document explains how to upgrade a site to a newer version of CKAN. It will
walk you through the steps to upgrade your CKAN site to a newer version of CKAN.

.. include:: /_supported_versions.rst

1. Prepare the upgrade
======================

*  Before upgrading your version of CKAN you should check that any custom
   templates or extensions you're using work with the new version of CKAN.
   For example, you could install the new version of CKAN in a new virtual
   environment and use that to test your templates and extensions.

* You should also read the :doc:`/changelog` to see if there are any extra
  notes to be aware of when upgrading to the new version.

.. warning:: You should always **backup your CKAN database** before upgrading CKAN. If something
   goes wrong with the CKAN upgrade you can use the backup to restore the database
   to its pre-upgrade state. See :ref:`Backup your CKAN database <db dumping and loading>`


2. Upgrade CKAN
===============

The process of upgrading CKAN differs depending on whether you have a package
install or a source install of CKAN, and whether you're upgrading to a
:ref:`major, minor or patch release <releases>` of CKAN. Follow the
appropriate one of these documents:

.. toctree::
    :maxdepth: 1

    upgrade-package-to-patch-release
    upgrade-package-to-minor-release
    upgrade-source
    upgrade-to-python3


.. seealso::

   :doc:`/maintaining/releases`
     Information about the different CKAN releases and the officially supported
     versions.

   :doc:`/changelog`
     The changelog lists all CKAN releases and the main changes introduced in
     each release.

   :doc:`/contributing/release-process`
     Documentation of the process that the CKAN developers follow to do a
     CKAN release.
