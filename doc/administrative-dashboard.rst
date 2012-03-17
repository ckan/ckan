=============================
CKAN Administrative Dashboard
=============================

CKAN provides an administrative dashboard available to Sysadmin Administrators.
The dashboard allows you to:

* Create and remove sysadmins
* Edit general system level authorization
* Manage the 'trash' bin (i.e. datasets or revisions that have been marked as deleted)

The dashboard is located, relative to your site root, at ``/ckan-admin/``.

.. note:: To create your first sysadmin you cannot use Dashboard as you will
          not yet have access! Instead create a sysadmin using the command line
          ``paster`` by running the following command::
          
            paster sysadmin -h

Setting System-Level Roles
==========================

Authorization interface is located at: ``/ckan-admin/authz``

This page allows you to see and change the users and authorization groups who
have 'roles' on the 'System Object'. In a standard installation, there are four
'roles' which a user can have on the System (or on any object):

* admin (administrator)

  * Having an admin role on the System objects means you are a System Administrator
    and may carry out **any** operation on any object.

    .. warning:: Once a person is an system administrator, they can carry out
                 **any** operatoin on the system including **destructive**
                 ones. Grant System Administrator access with care!

* reader (Read action allowed)

  * Without read access a site user or visitor will not be able to see
    anything except the login page, even the page which allows them to
    create an account, so they're locked out forever unless they already
    have a valid account.

* editor (Update action allowed) 
* anon-editor

.. note:: these roles can be applied to users on your system as well as to
          'pseudo-users' like 'visitor', which stands for anyone who accesses
          the site whether logged in or not (see :doc:`authorization` for more
          on permissions and roles).

Make Someone a Sysadmin
=======================

Given the user the role 'admin'.

The Trash
=========

When you delete datasets or revisions they go into the 'trash'. The contents of
the trash can be viewed by System Administrators at: ``/ckan-admin/trash``.

Contents of the trash can be removed permanently (and **irreversibly**) by
going to the trash page and selecting the purge option.

