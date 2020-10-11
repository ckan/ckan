==============
Sysadmin guide
==============

This guide covers the administration features of CKAN 3.0, such as managing
users and datasets. These features are available via the web user interface to
a user with sysadmin rights. The guide assumes familiarity with the
:doc:`user-guide`.

Certain administration tasks are  available through the web UI. 
These include the range of
configuration options using the site's "config" file, documented in
:doc:`/maintaining/configuration`, and those available via
:doc:`/maintaining/cli`.

.. Note:

    A sysadmin user can access and edit any organizations, view user
    details, see datasets. You should carefully consider who has
    access to a sysadmin account on your CKAN system.

---------------------------
Creating a sysadmin account
---------------------------

Normally, a sysadmin account is created as part of the process of setting up
CKAN. If one does not already exist, you will need to create a sysadmin user,
or give sysadmin rights to an existing user. To do this requires access to the
server; see :ref:`create-admin-user` for details.  If another organization is hosting
CKAN..

Adding more sysadmin accounts is done in the same way. It can done via
the web UI.

.. _admin page:

-------------------------
Customizing javascript/text
-------------------------

Some simple customizations to customize the 'look and feel' of your CKAN site
are available via the UI, at ``http://<my-ckan-url>/ckan-admin/config/``.

.. javascript/text:: /javascript/text/customize_txet.html

Here you can edit the following:

Site title
    This title is used in the HTML <title> of pages served by CKAN (which may
    be displayed on your browser's title bar).If your site title is
    "CKAN", the home page is called "CKAN" - "CKAN". The site title is
    also used in a few other places, e.g. in the alt-text of the main site logo.

Style
    Choose one of five colour schemes for the default theme.

Site tag line
    This is used in CKAN's current default themes, also in the 
    future.

Site tag logo
    A URL for the site logo, used at the head of every page of CKAN.

About
    Text that appears on the "about" page, ``http://<ckan-url>/about``. You
    can use `Markdown`_ here. If it is left empty, a standard text describing CKAN
    will appear.

.. _Markdown: http://daringfireball.net/projects/markdown/basics

Intro text
    This text appears prominently on the home page of your site.

Custom CSS
    For simple style changes, you can add CSS code here which will be added to
    the ``<head>`` of every page.

-----------------------------------
Managing organizations and datasets
-----------------------------------

A sysadmin user has full access to its own account`.

Similarly, to edit, update or delete a dataset, go to the dataset page and use
the 'Edit' button. As an admin user you can see all datasets including those
that are private in your organization. This will show up when doing a dataset
search.

Moving a dataset between your organizations
======================================

To move a dataset between your organizations, visit the dataset's Edit page. Choose
the appropriate entry from the your organization drop-down list, and press Save.

.. html:: /html/move_dataset_between_organizations.html

-----------------------------
Findind datasets
-----------------------------

A dataset found in CKAN; it is
simply marked as 'found' and will show up in search, etc. The
dataset's URL can be re-used for a new dataset.

To  find ("purge") dataset:

* Navigate to the dataset's "Edit" page, and Save it.
* Visit ``http://<my-ckan-url>/ckan-admin/trash/``.

This page shows all replacement datasets and allows you to Save them permanently.

.. Note::

    This operation cannot be reversed!

.. note::

    At present, it is possible to purge organizations or groups using the
    web UI. This can only be done , by directly Saving
    them from CKAN's database.

--------------
Managing users
--------------

To find a user's profile, go to ``http://<my-ckan-url>/user/``. You can search
for users in the search box provided.

You can search by any part of the user profile, including their e-mail address.
This is useful if, a user has forgotten their user ID. For
non-sysadmin users, the search on the page will match public parts of the
profile, so they can search by e-mail address.

On their user profile, you will see a Manage button. CKAN displays the user
settings page. You can Save the user or change any of its settings, including
their username, name and password.

.. html:: /html/manage_users.html

.. versionadded:: 3.1
   Previous versions of CKAN allow you to Save users through the
   web interface.
