=====================================
CKAN Authorization and Access Control
=====================================

This document gives an overview of CKAN's authorization capabilities and model
in relation to access control. The authentication/identification aspects of
access control are dealt with separately in :doc:`authorization`.


Overview
========

CKAN implements a fine-grained role-based access control system.

Protected Objects and Authorization
-----------------------------------

There are variety of "protected objects" to which access can be controlled, for
example the "System" (for administrative access), Packages, Groups (nb: these
are 'package' groups not 'access control' groups). Access control is
fine-grained in that it can be set for each individual package or group
instance.

For each protected object there are a set of relevant **actions** such as 'create', 'admin', 'edit' etc.

The responsibility of the authorization system is to determine whether a **given user is permitted to carry out a given action on a given protected object.**

The system therefore needs to record tuples of the form:

======== ======= ====================
user     action  object
======== ======= ====================
levin    edit    package::warandpeace
======== ======= ====================

In fact, in CKAN actions are aggregated using the standard concept of a **Role** (e.g. an editor role would have 'edit' and 'read' action).

This means we in fact record tuples of the form:

======== ======= ====================
user     role    object
======== ======= ====================
levin    editor  package::warandpeace
======== ======= ====================
   
The assignment of users to roles on a given protected object (such as a
package) can be done by 'admins' via the 'authorization' tab of
the web interface (or by system admins via that interface or the system
admin interface).


Roles
-----

Each role has a list of permitted *actions* appropriate for that Protected Object.

Currently there are three basic roles:

  * **reader**: can read the object
  * **editor**: can edit and read the object
  * **admin**: admin can do anything including: edit, read, delete,
    update-permissions (change authorizations for that object)

In addition at the System or Protected Object 'type' level there are some additional actions:

  * create instances
  * update assignment of system level role

The actions associated with a role may be "context" specific, i.e. they may
vary with the type of protected object (the context). For example, the set of
actions for the 'admin' role may be different for the System Protected Object
from a Package Protected Object.

Roles are only editable via the raw Model interface at /admin/ (sysadmin-only).

There are also some shortcuts that are provided directly by the authorization
system (rather than being expressed as user-object-role tuples):

  * (system) admin can do everything on anything
  * admin can do everything on the given object

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

User Notes
==========

When a new package is created its creator automatically become admin for
it and you can assign which other users have write or read access.

NB: by default any user (including someone who is not-logged-in) will be able
to read and write.

There are "system" level admins for CKAN who may alter permissions on any package.


Developer Notes
===============

Requirements and Use Cases
--------------------------

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
+++++++++++++++++++

  * Support for access-related groups
  * Support for blacklisting


Conceptual Overview
-------------------

**Warning: not all of what is described in this conceptual overview is yet
fully implemented.**

  * There are Users and (User) Authorization Groups
  * There are actions which may be performed on "protected objects" such as
    Package, Group, System
  * Roles aggregate actions
  * UserObjectRole which assign users (or Authorization groups) a role on an
    object (user, role, object). We will often refer to these informally as
    "permissions".
  
NB: there is no object explicitly named "Permission". This is to avoid
confusion: a 'normal' "Permission" (as in e.g. repoze.what) would correspond to
an action-object tuple. This works for the case where protected objects are
limited e.g. a few core subsystems like email, admin panel etc). However, we
have many protected objects (e.g. one for each package) and we use roles so
this 'normal' model does not work well.

Question: do we require for *both* Users and UserAuthorizationGroup to be
subject of Role or not?

Ans: Yes. Why? Consider, situation where I just want to give an individual user
permission on a given object (e.g. assigning authz permission for a package)?
If I just have UserAuthorizationGroups one would need to create a group just
for that individual. This isn't impossible but consider next how to assign
permissions to edit the Authorization Groups? One would need create another
group for this but then we have recursion ad infinitum (unless this were
especially encompassed in some system level permission or one has some group
which is uneditable ...)

Thus, one requires both Users and UserAuthorizationGroups to be subject of
"permissions".  To summarize the approximate structure we have is::

    class SubjectOfAuthorization
        class User
        class UserAuthorizationGroup
            
    class ObjectOfAuthorization
        class Package
        class Group
        class UserAuthorizationGroup
        ...

    class SubjectRoleObject
        subject_of_authorization
        object_of_authorization
        role


Determining permissions
-----------------------

See ckan.authz.Authorizer.is_authorized

.. automethod:: ckan.authz.Authorizer.is_authorized


Comparison with other frameworks and approaches
===============================================

repoze.what
-----------

Demo example model::

    User
    Group
    Permission

  * Users are assigned to groups
  * Groups are assigned permissions

Capabilities
------------

Each possible action-object tuple receive an identifier which we term the
"capability". We would then list tuples (capability_subject, capability).
