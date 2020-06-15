===============================
Organizations and authorization
===============================

CKAN's authorization system controls which users are allowed to carry out which
actions on the site. All actions that users can carry out on a CKAN site are
controlled by the authorization system. For example, the authorization system
controls who can register new user accounts, delete user accounts, or create,
edit and delete datasets, groups and organizations.

Authorization in CKAN can be controlled in four ways:

1. Organizations
2. Dataset collaborators
3. Configuration file options
4. Extensions

The following sections explain each of the four methods in turn.

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
of the dataset's organization.  Private datasets are not shown in dataset searches
unless the logged in user (or the user identified via an API key)
has permission to access them.

When a user joins an organization, an organization admin gives them one of
three roles: member, editor or admin.

A **member** can:

* View the organization's private datasets.

An **editor** can do everything a **member** can plus:

* Add new datasets to the organization
* Edit or delete any of the organization's datasets
* Make datasets public or private.

An organization **admin** can do everything as **editor** plus:

* Add users to the organization, and choose whether to make the new user a
  member, editor or admin
* Change the role of any user in the organization, including other admin users
* Remove members, editors or other admins from the organization
* Edit the organization itself (for example: change the organization's title,
  description or image)
* Delete the organization

When a user creates a new organization, they automatically become the first
admin of that organization.

.. _dataset_collaborators:

Dataset collaborators
---------------------

.. versionchanged:: 2.9
   Dataset collaborators were introduced in CKAN 2.9

In addition to traditional organization-based permissions, CKAN instances can also enable
the dataset collaborators feature, which allows dataset-level authorization. This provides
more granular control over who can access and modify datasets that belong to an organization,
or allows authorization setups not based on organizations. It works by allowing users with
appropriate permissions to give permissions to other users over individual datasets, regardless
of what organization they belong to.

Dataset collaborators are not enabled by default, you need to activate it by
setting :ref:`ckan.auth.allow_dataset_collaborators` to ``True``.

By default, only Administrators of the organization a dataset belongs to can add collaborators
to a dataset. When adding them, they can choose between two roles: member and editor.

A **member** can:

* View the dataset if it is private.

An **editor** can do everything a **member** can plus:

* Make the dataset public or private.
* Edit or delete the dataset (including assigning it to an organization)

In addition, if :ref:`ckan.auth.allow_admin_collaborators` is set to ``True``, collaborators
can have another role: admin.

An **admin** collaborator can do everything an **editor** can plus:

* Add collaborators to the dataset, and choose whether to make them a
  member, editor or admin (if enabled)
* Change the role of any collaborator in the dataset, including other admin users
* Remove collaborators of any role from the dataset

If the ``ckan.auth.allow_admin_collaborators`` setting is turned off in a site where admin collaborators have already been created, existing collaborators with role **admin** will no longer be able to manage collaborators, but they will still be able to edit and access the datasets that they are assigned to (ie they will have the same permissions as an **editor**.

If the global ``ckan.auth.allow_dataset_collaborators`` setting is turned off in a site where collaborators have already been created, collaborators will no longer have permissions on the datasets they are assigned to, and normal organization-based permissions will be in place.

.. warning:: When turning off this setting, you must reindex all datasets to update the permission labels, in order to prevent access to private datasets to the previous collaborators.

By default, collaborators can not change the owner organization of a dataset unless they are admins or editors in both the source and destination organizations. To allow collaborators to change the owner organization even if they don't belong to the source organization, set :ref:`ckan.auth.allow_collaborators_to_change_owner_org` to ``True``.

Dataset collaborators can be used with other authorization settings to create custom authentication scenarios. For instance on instances where datasets don't need to belong to an organization (both :ref:`ckan.auth.create_dataset_if_not_in_organization` and :ref:`ckan.auth.create_unowned_dataset` are ``True``), the user that originally created a dataset can also add collaborators to it (allowing admin collaborators or not depending on the ``ckan.auth.allow_admin_collaborators`` setting). Note that in this case though, if the dataset is assigned to an organization, the original creator might no longer be able to access and edit, as organization permissions take precedence over collaborators ones.



Configuration File Options
--------------------------

The following configuration file options can be used to customize CKAN's
authorization behavior:

.. include:: /maintaining/configuration.rst
    :start-after: start_config-authorization
    :end-before: end_config-authorization

Extensions
----------

CKAN extensions can implement custom authorization rules by overriding the
authorization functions that CKAN uses. This is done by implementing the
:py:class:`~ckan.plugins.interfaces.IAuthFunctions` plugin interface.

Dataset visibility is determined by permission labels stored in the
search index.
Implement the :py:class:`~ckan.plugins.interfaces.IPermissionLabels`
plugin interface then :ref:`rebuild your search index <rebuild search index>`
to change your dataset visibility rules. There is no
no need to override the ``package_show`` auth function, it will inherit
these changes automatically.

To get started with writing CKAN extensions, see :doc:`/extensions/index`.
