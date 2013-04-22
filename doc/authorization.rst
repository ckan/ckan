=============
Authorization
=============

.. versionchanged:: 2.0
   Previous versions of CKAN used a different authorization system.

CKAN's authorization system controls which users are allowed to carry out which
actions on the site. All actions that users can carry out on a CKAN site are
controlled by the authorization system. For example, who can register new user
accounts, delete user accounts, or create, edit and delete datasets, groups and
organizations.

Authorization in CKAN can be controlled in three ways:

1. Organizations
2. Configuration file options
3. Authorization functions

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
* Edit and delete the organization's datasets
* Add new datasets to the organization
* Make  datasets public or private.
* Add users to the organization, and choose whether to make the new user an
  member, editor or admin
* Change the role of any user in the organization, including other admin users
* Remove members, editors or other admins from the organization

An **editor** can:

* View the organization's private datasets
* Edit and delete the organization's datasets

A **member** of an organization can view the organization's private datasets.

When a user creates a new organization, they automatically become the first
admin of that organization.

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


Authorization Functions
-----------------------

Each logic function in CKAN has a corresponding authorization function.
These functions are in files in the `ckan/logic/auth` directory.  These
functions are used to determine if the user has the permission to perform
the given action.  Because CKAN allows these functions to be redefined by
extensions it is important never to directly call these functions but to
call them via the `ckan.logic.check_access()` function.  If the user does
not have permission a `NotAuthorized` exception is raised.

.. note:: extensions should access both `check_access` and `NotAuthorized`
  via the plugins toolkit - see the section on Extensions for more details.

Templates can access authorization functions via the `h.check_access()`
template helper function.
