=============
Authorization
=============

.. note:: Authorization in ckan 2.0 works differently from previous versions.

Authorization in CKAN is controlled in a number of ways.

* Config settings
* Authorization functions
* Organizations

This document aims to explain them.

Config Settings
---------------

Several .ini config options can be set to change the behavior of CKAN.
These include

* `ckan.auth.anon_create_dataset` - allows non registered users to create datasets, default: False
* `ckan.auth.create_dataset_if_not_in_organization` users not in organizations can create datasets, default: True
* `ckan.auth.create_unowned_dataset` allow the creation of datasets not owned by an organization, default: True
* `ckan.auth.user_create_groups` allow registered users to create their own group, default: True
* `ckan.auth.user_create_organizations` allow registered users to create their own organization, default: True
* `ckan.auth.user_delete_groups` allow non system administrator users to delete groups, default: True
* `ckan.auth.user_delete_organizations` allow non system administrator users to delete organizations, default: True
* `ckan.auth.create_user_via_api` allow non system administrator users to be created via the API, default: False


Authorization functions
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

* Admin:  An organizations Administrator have all permissions for that
  organization, including adding or removing members.

* Editor: This roles allows editing of datasets.

* Member: Members of an organization can view datasets belonging to an
  organization including private datasets.

When a user creates an organization (assuming they have permission to do
this) then they are made an Admin of that organization.
