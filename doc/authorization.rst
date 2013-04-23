=============
Authorization
=============

.. versionchanged:: 2.0
   Previous versions of CKAN used a different authorization system.

CKAN's authorization system controls which users are allowed to carry out which
actions on the site. All actions that users can carry out on a CKAN site are
controlled by the authorization system. For example, the authorization system
controls who can register new user accounts, delete user accounts, or create,
edit and delete datasets, groups and organizations.

Authorization in CKAN can be controlled in three ways:

1. Organizations
2. Configuration file options
3. Extensions

The following sections explain each of the three methods in turn.

.. note::

   An **organization admin** in CKAN is an administrator of a particular
   organization within the site, with control over that organization and its
   members and datasets. A **sysadmin** is an administrator of the site itself.
   Sysadmins can always do everything, including adding, editing and deleting
   datasets, organizations and groups, regardless of the organization roles and
   configuration options described below.

Organizations
-------------


Organizations are the primary way to control who can see, create and update
datasets in CKAN. Each dataset can belong to a single organization, and each
organization controls access to its datasets.

Datasets can be marked as public or private.  Public datasets are visible to
everyone. Private datasets can only be seen by logged-in users who are members
of the dataset's organization.  Private datasets are not shown in general
dataset searches but are shown in dataset searches within the organization.

When a user joins an organization, an organization admin gives them one of
three roles: member, editor or admin.

An organization **admin** can:

* View the organization's private datasets
* Add new datasets to the organization
* Edit or delete any of the organization's datasets
* Make  datasets public or private.
* Add users to the organization, and choose whether to make the new user a
  member, editor or admin
* Change the role of any user in the organization, including other admin users
* Remove members, editors or other admins from the organization
* Edit the organization itself (for example: change the organization's title,
  description or image)
* Delete the organization

An **editor** can:

* View the organization's private datasets
* Add new datasets to the organization
* Edit or delete any of the organization's datasets

A **member** can:

* View the organization's private datasets.


Configuration File Options
--------------------------

The following configuration file options can be used to customize CKAN's
authorization behavior:

``ckan.auth.anon_create_dataset``
  Allow users to create datasets without registering and logging in,
  default: false.

``ckan.auth.create_unowned_dataset``
  Allow the creation of datasets not owned by any organization, default: true.

``ckan.auth.create_dataset_if_not_in_organization``
  Allow users who are not members of any organization to create datasets,
  default: true. ``create_unowned_dataset`` must also be true, otherwise
  setting ``create_dataset_if_not_in_organization`` to true is meaningless.

``ckan.auth.user_create_groups``
  Allow users to create groups, default: true.

``ckan.auth.user_create_organizations``
  Allow users to create organizations, default: true.

``ckan.auth.user_delete_groups``
  Allow users to delete groups, default: true.

``ckan.auth.user_delete_organizations``
  Allow users to delete organizations, default: true.

``ckan.auth.create_user_via_api``
  Allow new user accounts to be created via the API, default: false.


Extensions
----------

CKAN allows extensions to change the authorization rules used.  Please see
individual extensions for details.

.. todo::

  Insert cross-reference to ``IAuthFunctions`` docs.
