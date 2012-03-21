==========================
Set and Manage Permissions
==========================

CKAN implements a fine-grained role-based access control system.

This section describes:

* :ref:`permissions-overview`. An overview of the concepts underlying CKAN authorization: objects, actions and roles.
* :ref:`permissions-default`. The default permissions in CKAN.
* :ref:`permissions-manage`. Managing and setting permissions.
* :ref:`permissions-publisher-mode`. Suitable for systems where you want to limit write access to CKAN.

.. _permissions-overview:

Overview
--------

In a nutshell: for a particular **object** (e.g. a dataset) a CKAN **user** can be assigned a **role** (e.g. editor) which allows permitted **actions** (e.g. read, edit).

In more detail, these concepts are as follows:

* There are **objects** to which access can be controlled, such as datasets and groups.
* For each object there are a set of relevant **actions**, such as create and edit, which users can perform on the object.
* To simplify mapping users to actions and objects, actions are aggregated into a set of **roles**. For example, an editor role would automatically have edit and read actions.
* Finally, CKAN has registered **users**.

Recent support for authorization profiles has been implemented using a publisher/group based profile that is described in :doc:`publisher-profile`.

Objects
+++++++

Permissions are controlled per object: access can be controlled for an individual
dataset, group or authorization group instance. Current objects include
**datasets**, dataset **groups**, **authorization groups** and the **system**.

* A dataset is the basic CKAN concept of metadata about a dataset.
* A group of datasets can be set up to specify which users have permission to add or remove datasets from the group.
* Users can be assigned to authorization groups, to increase flexibility. Instead of specifying the privileges of specific users on a dataset or group, you can also specify a set of users that share the same rights. To do that, an authorization group can be set up and users can be added to it. Authorization groups are both the object of authorization (i.e. one can have several roles with regards to an authorization group, such as being allowed to read or edit it) and the subject of authorization (i.e. they can be assigned roles on other objects which will apply to their members, such as the group having edit rights on a particular group).
* Finally, the system object is special, serving as an object for assignments that do not relate to a specific object. For example, creating a dataset cannot be linked to a specific dataset instance, and is therefore a operation.


Actions
+++++++

**Actions** are defined in the Action enumeration in ``ckan/model/authz.py`` and currently include: **edit**, **change-state**, **read**, **purge**, **edit-permissions**, **create-dataset**, **create-group**, **create-authorization-group**, **read-site**, **read-user**, **create-user**.

As noted above, some of these (e.g. **read**) have meaning for any type of object, while some (e.g. **create-dataset**) can not be associated with any particular object, and are therefore only associated with the system object.

The **read-site** action (associated with the system object) allows or denies access to pages not associated with specific objects. These currently include:

 * Dataset search
 * Group index
 * Tags index
 * Authorization Group index
 * All requests to the API (on top of any other authorization requirements)

There are also some shortcuts that are provided directly by the authorization
system (rather than being expressed as subject-object-role tuples):

  * A user given the **admin** right for the **system** object is a 'sysadmin' and can perform any action on any object. (A shortcut for creating a sysadmin is by using the ``paster sysadmin`` command.)
  * A user given the **admin** right for a particular object can perform any action on that object.

Roles
+++++

Each **role** has a list of permitted actions appropriate for a protected object.

Currently there are four basic roles:

  * **reader**: can read the object
  * **anon_editor**: anonymous users (i.e. not logged in) can edit and read the object
  * **editor**: can edit, read and create new objects
  * **admin**: admin can do anything including: edit, read, delete,
    update-permissions (change authorizations for that object)

You can add other roles if these defaults are not sufficient for your system.

.. warning:: If the broad idea of these basic roles and their actions is not suitable for your CKAN system, we suggest you create new roles, rather than edit the basic roles. If the definition of a role changes but its name does not, it is likely to confuse administrators and cause problems for CKAN upgrades and extensions.

.. note:: When you install a new CKAN extension, or upgrade your version of CKAN, new actions may be created, and permissions given to these basic roles, in line with the broad intention of the roles.

Users
+++++

You can manage CKAN users via the command line with the ``paster user`` command - for more information, see :ref:`paster-user`.

There are two special *pseudo-users* in CKAN, **visitor** and **logged-in**. These are used to refer to special sets of users, respectively those who are a) not logged-in ("visitor") and b) logged-in ("logged-in").

The ``default_roles`` config option in the CKAN config file lets you set the default authorization roles (i.e. permissions) for these two types of users. For more information, see :doc:`configuration`.


.. _permissions-default:

Default Permissions
-------------------

CKAN ships with the following default permissions:

* When a new dataset is created, its creator automatically becomes **admin** for it. This user can then change permissions for other users.
* By default, any other user (including both visitors and logged-ins) can read and write to this dataset.

These defaults can be changed in the CKAN config - see ``default_roles`` in :doc:`configuration`.


.. _permissions-manage:

Managing Permissions
--------------------

The assignment of users and authorization groups to roles on a given
protected object (such as a dataset) can be done by 'admins' via the
'authorization' tab of the web interface (or by sysadmins via that
interface or the system admin interface).

There is also a command-line authorization manager, detailed below.

Command-line authorization management
+++++++++++++++++++++++++++++++++++++

Although the admin extension provides a Web interface for managing authorization,
there is a set of more powerful ``paster`` commands for fine-grained control
(see :doc:`paster`).

The ``rights`` command is used to configure the authorization roles of
a specific user on a given object within the system.

For example, to list all assigned rights in the system (which you can then grep if needed)::

    paster --plugin=ckan rights -c my.ini list

The ``rights make`` command lets you assign specific permissions. For example, to give the user named **bar** the **admin** role on the dataset foo::

    paster --plugin=ckan rights -c my.ini make bar admin dataset:foo

As well as users and datasets, you can assign rights to other objects. These
include authorization groups, dataset groups and the system as a whole.

For example, to make the user 'chef' a system-wide admin::

    paster --plugin=ckan rights -c my.ini make chef admin system

Or to allow all members of authorization group 'foo' to edit group 'bar'::

    paster --plugin=ckan rights -c my.ini make agroup:foo edit \
        group:bar

To revoke one of the roles assigned using ``rights make``, the ``rights remove`` command
is available. For example, to remove **bar**'s **admin** role on the foo dataset::

    paster --plugin=ckan rights -c my.ini remove bar admin dataset:foo

The ``roles`` command lists and modifies the assignment of actions to
roles.

To list all role assignments::

    paster --plugin=ckan roles -c my.ini list

To remove the 'create-package' action from the 'editor' role::

    paster --plugin=ckan roles -c my.ini deny editor create-package

And to re-assign 'create-package' to the 'editor' role::

    paster --plugin=ckan roles -c my.ini allow editor create-package

For more help on either of these commands, you can use ``--help`` (as described in :ref:`paster-help`)::

    paster --plugin=ckan roles --help
    paster --plugin=ckan rights --help


.. _permissions-publisher-mode:

Openness Modes
--------------

CKAN instances can be configured to operate in a range of authorization modes, with varying openness to edit. Here are some examples with details of how to set-up and convert between them.


1. Anonymous Edit Mode
++++++++++++++++++++++

Anyone can edit and create datasets without logging in. This is the default for CKAN out of the box.




2. Logged-in Edit Mode
++++++++++++++++++++++

You need to log-in and create/edit datasets. Anyone can create an account.

To operate in this mode:

1. First, change the visitor (any non-logged in user) rights from being able to create and edit datasets to just reading them::

     paster rights make visitor reader system
     paster rights make visitor reader package:all
     paster rights remove visitor anon_editor package:all
     paster rights remove visitor anon_editor system

2. Change the default rights for newly created datasets. Do this by using these values in your config file (see :doc:`configuration`)::

     ckan.default_roles.Package = {"visitor": ["reader"], "logged_in": ["editor"]}
     ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["editor"]}
     ckan.default_roles.System = {"visitor": ["reader"], "logged_in": ["editor"]}
     ckan.default_roles.AuthorizationGroup = {"visitor": ["reader"], "logged_in": ["editor"]}


3. Publisher Mode
+++++++++++++++++

This allows edits only from authorized users. It is designed for installations where you wish to limit write access to CKAN and orient the system around specific publishing groups (e.g. government departments or specific institutions).

The key features are:

* Datasets are assigned to a specific publishing group.
* Only users associated to that group are able to create or update datasets associated to that group.

To operate in this mode:

1. First, remove the general public's rights to create and edit datasets::

     paster rights remove visitor anon_editor package:all
     paster rights remove logged_in editor package:all
     paster rights remove visitor anon_editor system
     paster rights remove logged_in editor system

2. If logged-in users have already created datasets in your system, you may also wish to remove their admin rights. For example::

     paster rights remove bob admin package:all

3. Change the default rights for newly created datasets. Do this by using these values in your config file (see :doc:`configuration`)::

     ckan.default_roles.Package = {"visitor": ["reader"], "logged_in": ["reader"]}
     ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["reader"]}
     ckan.default_roles.System = {"visitor": ["reader"], "logged_in": ["reader"]}
     ckan.default_roles.AuthorizationGroup = {"visitor": ["reader"], "logged_in": ["reader"]}

Note you can also restrict dataset edits by a user's authorization group.
