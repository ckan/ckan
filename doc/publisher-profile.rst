==============================
Publisher Profile and Workflow
==============================

.. versionadded:: 1.6.1

The Publisher workflow in CKAN is designed to support a setup in which datasets
are managed by a "Publisher" organization. Users can become members of one (or
more) Publishers and their membership determines what datasets they have access
to.

Specifically, the workflow looks like:

* A User joins or creates a Publisher

  * If creator of the Publisher User becomes administrator of the Publisher
    otherwise they become a Member.
  * Creation of new Publishers must be approved by a System Administrator
  * New Members must be approved by the Group Administrator
  
* User creates a dataset. On creation User must assign this dataset to a
  specific publisher (and can only assign to a Publisher of which User is a
  member)

  * Other members of that Publisher can then edit and update this dataset

This setup is a natural one for many situations. For example:

 * Government. Publishers correspond to Departments or Ministries (or other
   organizational groups)
 * Academia: Publishers again correspond to Departments or research groups


.. _publisher-configuration:
Enabling and Configuring the Publisher Profile
==============================================

To switch CKAN to use the publisher profile workflow you need to set the
following configuration option::

	ckan.auth.profile = publisher

Setting auth.profile to publisher will enable the publisher authorization
profile. Setting it to nothing, or if it is not present will force CKAN to use
the default profile.


Technical Overview
==================

* Publishers are a specialization of CKAN Groups. As such they retain many of
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

