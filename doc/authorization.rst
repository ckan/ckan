=====================================
CKAN Authorization and Access Control
=====================================

This document gives an overview of CKAN's authorization capabilities and model
in relation to access control. The authentication/identification aspects of
access control are dealt with separately in the :ref:authorization.rst.


Overview
========

In essence, CKAN implements a standard role-based access control model.

Protected Objects and Authorization
-----------------------------------

There are variety of "protected objects" to which access can be controlled, for
example the "System" (e.g. in relation to administrative access), Packages,
Groups (nb: these are 'package' groups not 'access control' groups).

For each protected object there are a set of relevant **actions** such as 'create', 'admin', 'edit' etc.

The responsibility of the authorization system is to determine whether a **given user is permitted to carry out a given action on a given protected object.**

The system therefore needs to record tuples of the form::

  user    |  action | object
  # e.g.
  levin   |  edit   | package::warandpeace

In fact, in CKAN actions are aggregated using the standard concept of a **Role** (e.g. an editor role would have 'edit' and 'read' action).

This means we in fact record tuples of the form::

  user    |  role   | object
  levin   |  editor | package::warandpeace
   
The assignment of users to roles on a given protection object (such as a
package) can be done by 'admins' via the 'authorization' tab of
the web interface (or by system admins via that interface or the system
admin interface).


Roles
-----

Each role has a list of permitted *actions* appropriate for that Protected Object.

Currently there are three basic roles:

 * An 'admin' can do anything (includes package/group deletion & changing user roles)
 * An 'editor' can edit or read
 * A 'reader' can read

Roles are only editable via the raw Model interface at /admin/ (sysadmin-only).

Examples
--------

Example 1: Package 'paper-industry-stats':

  * David Brent is an 'admin'
  * Gareth Keenan is an 'editor'
  * Logged-in is an 'reader' (This is a special user, meaning 'anyone who is
    logged in')
  * Visitor is an 'reader' (Another special user, meaning 'anyone')

That is, Gareth and David can edit this package, but only Gareth can assign
roles (privileges) to new team members. Anyone can see (read) the package.


Example 2: The current default for new packages is:

  * the user who creates it is an 'admin'
  * Visitor and Logged-in are both an 'editor' and 'reader'

NB: "Visitor" and "Logged-in" are special "pseudo-users" used as a way of
concretely referring to the special sets of users, namely those that are a) not
logged-in ("visitor") and b) logged-in ("Logged-in")


Design Notes
============

When a new package is created you as the creator automatically become admin for
it and you can assign which other users have write or read access.

NB: by default any user (including someone who is not-logged-in) will be able
to read and write.

There are "system" level admins for CKAN who may alter permissions on any package.

Use Cases
---------

  * A user means someone who is logged in.
  * A visitor means someone who is not logged in.
  * An protected object is the subject of a permission (either a user or a
    pseudo-user)
  * There are roles named: Admin, Reader, Writer

  1. A visitor visits a package page and reads the content
  2. A visitor visits a package page and edits the package
  3. Ditto 1 for a user
  4. Ditto 2 for a user
  5. On package creation if done by a user and not a visitor then user is made
     the 'admin'
  6. An admin of a package adds a user as an admin
  7. An admin of a package removes a user as an admin
  8. Ditto for admin re. editor
  9. Ditto for admin re. reader
  10. We wish to be able assign roles to 2 specific entire groups in addition
      to specific users: 'visitor', 'users'. These will be termed pseudo-users
      as we do not have AC 'groups' as such.
  11. The sysadmin alters the assignment of entities to roles for any package
  12. A visitor goes to a package where the editor role does not include
      'visitor' pseudo-user. They are unable to edit the package.
  13. Ditto for user where users pseudo-user does not have editor role and user
      is not an editor for the package
  14. Ditto 12 re reader role.
  15. Ditto 13 re reader role.
  16. Try to edit over REST interface a package for which 'visitor' has Editor
      role, but no API is supplied. Not allowed.


Not Yet Implemented
-------------------

  * Support for access-related groups
  * Support for blacklisting


Implementation Details
----------------------

Role assignment::

        Context
  Protected Object ----> Role

  E.g. a user is assigned to a given role for a particular package.

      Context
  Role ----> Action/Permission/Capability (on an Object e.g. a Package)


Package level:

  * Package Roles: admin, editor, reader
  * Entities: xyz@xyz.com (user), pseudo-users 'visitor'
  * Assignment of entities to roles in a given context (the package)
  * Roles give permissions (in a given context)
    * admin -> update assignment to roles, delete package, plus editor
    * editor -> update package plus reader
    * reader -> read package

System level permissions:

  * Roles: admin, ?
  * create package 
  * update assignment of system level role

Shortcuts:

  * sysadmin can do everything on anything
  * ? admin can do everything on the given object


Determining permissions
-----------------------

See ckan.authz.Authorizer.is_authorized

.. automethod:: ckan.authz.Authorizer.is_authorized


DB Sketch
---------

  * role enum: admin, editor, reader
  * action enum: read, edit, delete (to deleted state), purge (destroy),
    edit-permissions, create
  * context enum: system, package, tag, group, revision

role-action table::

    role | context | action
    admin| package | update
    admin| package | update-permissions
    admin| package | read
    editor| package | update
    editor| package | read

user-role table::

    username.id | context | objectid    | role
    xyz.id      | package | geonames.id | admin
    rgrp.id     | system  |             | admin
    visitor.id  | package | geonames.id | editor 
    visitor.id  | package | geonames.id | reader

