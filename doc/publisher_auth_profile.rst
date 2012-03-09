===============================
Publisher Authorization Profile
===============================

CKAN provides authorization profiles which will allow authorization to be performed based on group membership rather than individually assigned actions.

* :ref:`publisher-overview`. An overview of the concepts underlying CKAN's publisher profile.
* :ref:`publisher-configuration`. Configuring the publisher profile
* :ref:`publisher-usage`. Using the publisher profile

.. _publisher-overview:

Overview
--------

In a nutshell: authorization for most actions is granted based on shared membership of a group between the **user** and the **object** being manipulated.

In more detail, these concepts are as follows:

* **Objects** such as *groups*, *datasets* and *users* can be added as members of groups.
* Each user within a group has a capacity with which it can interact with the group, currently these are *editor* and *administrator*.
* Even though groups are hierarchical there must be an intersection of the user's groups and the **object**'s groups for permission to be granted, as long as the capacity is appropriate.  For instance, being an *editor* within a group does not necessarily grant authorization to edit the group.
* This means that individual permissions do not need to granted on a *user* by *user* basis, instead the user can just be added to the appropriate group.

.. _publisher-configuration:

Configuration
-------------

To configure CKAN to use the publisher profile a single entry should be added to the CKAN configuration see  :doc:`configuration`

Setting auth.profile to publisher will enable the publisher authorization profile.  Setting it to nothing, or if it is not present will force CKAN to use the default authorization profile.

Example::
	ckan.auth.profile = publisher

