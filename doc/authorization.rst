=============
Authorization
=============

.. note:: Authorization in ckan 2.0 works differently from previous versions.

Authorization in CKAN is controlled in a number of ways.

* Organizations
* Config settings

This document aims to explain them.

Organizations
-------------

From version 2.0 CKAN uses organizations as the primary way to control
access to datasets as well as giving permissions to users to perform actions
on datasets. Each dataset in CKAN can belong to a single organization.  The
organization that the dataset belongs to controls the permissions for all
datasets that it owns.

Datasets can be marked as public or private.  Public datasets are visible to
all users. Private datasets can only be seen by members of the organization
that owns the dataset.  Private datasets are not shown in general dataset
searches but are shown in dataset searches within the organization.

Organizations have members.  The members of an organization have a role.
Currently the roles available are.

``Admin``
  Administrators of an organization can add or remove members of the
  organization, as well as edit or delete the organization itself.  They can
  add, edit, view and delete datasets owned by the organization.  Admins can
  also make owned datasets public or private.  When a user creates a new
  organization, they automatically become the first administrator of that
  organization.

``Editor``
  Editors of an organization can view, edit, add and delete datasets as well
  as view any owned datasets.

``Member``
  Members of an organization can view datasets belonging to an organization
  including private datasets.


Config Settings
---------------

Several configuration file options can be set to change the behavior of CKAN.
These include

``ckan.auth.anon_create_dataset``
  allows non registered users to create datasets, default: False

``ckan.auth.create_dataset_if_not_in_organization``
  allow users who are not a member of any organization create datasets.
  This depends on option ``create_unowned_dataset``, default: True

``ckan.auth.create_unowned_dataset``
  allow the creation of datasets not owned by an organization, default: True

``ckan.auth.user_create_groups``
  allow registered users to create their own group, default: True

``ckan.auth.user_create_organizations``
  allow registered users to create their own organization, default: True

``ckan.auth.user_delete_groups``
  allow non system administrator users to delete groups, default: True

``ckan.auth.user_delete_organizations``
  allow non system administrator users to delete organizations, default: True

``ckan.auth.create_user_via_api``
  allow non system administrator users to be created via the API, default: False
