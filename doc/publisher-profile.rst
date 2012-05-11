==============================
Publisher Profile and Workflow
==============================

.. versionadded:: 1.7

The Publisher/Organization workflow in CKAN is designed to support a setup in which datasets
are managed by a "Publisher" organization. Users can become members of one (or
more) Organizations and their membership determines what datasets they have access
to.

Specifically, the workflow looks like:

* A User joins or creates an Organization

    * If the user is the creator of the Organization then they become administrator of the Organization.

    * Otherwise they become a Member.

* New Members must be added by the Organization Administrator, although anyone can request to join an Organization

* User creates a dataset. On creation User must assign this dataset to a
  specific organization (and can only assign to a organization of which User is a
  member)

  * Other members of that Organization can then edit and update this dataset

This setup is a natural one for many situations. For example:

 * Government. Organizations correspond to Departments or Ministries (or other
   organizational groups)

 * Academia: Organizations again correspond to Departments or research groups

Whilst organizations can currently belong to other organizations the publisher authorization profile currently only checks membership of the current organization.  Future versions of this extension may provide a configuration option to apply authorization checks hierarchically.

.. _publisher-configuration:

Enabling and Configuring the Publisher Profile
==============================================

To switch CKAN to use the authorization publisher profile you need to set the
following configuration option::

	ckan.auth.profile = publisher

Setting auth.profile to publisher will enable the publisher authorization
profile. Setting it to nothing, or if it is not present will force CKAN to use
the default profile.

To enable the default organization and organization dataset forms you should include
the following plugins in your configuration file::

  ckan.plugins = organizations organizations_dataset

Technical Overview
==================

* Organizations are a specialization of CKAN Groups. As such they retain many of
  their features.
* Authorization for most actions is granted based on shared membership of a
  group between the **user** and the **object** being manipulated.
* You can design custom forms for publisher sign up and editing.

In more detail, these concepts are as follows:

* :doc:`Domain Objects <domain-model>` such as *groups*, *datasets* and *users*
  can be added as members of groups.
* Each user within a group has a capacity with which it can interact with the
  group, currently these are *editor* and *administrator*.
* Even though groups are hierarchical there must be an intersection of the
  user's groups and the **object**'s groups for permission to be granted, as
  long as the capacity is appropriate.  For instance, being an *editor* within
  a group does not necessarily grant authorization to edit the group.
* This means that individual permissions do not need to granted on a *user* by
  *user* basis, instead the user can just be added to the appropriate group.

