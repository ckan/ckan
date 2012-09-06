
User Stories
============

These are the essential user stories (not all possible ones) to give a sense of the purpose of Organization and Groups. 

Organizations and Groups
++++++++++++++++++++++++

* Anyone should be able to see a list of all organisations/groups and 
  see all the datasets belonging to them that are marked as public.
* As a sysadmin I want to be able to create an organization/group.
* As a catalog creator I want to be able to decide if a public user
  can create their own organization/group. (If the user can create a group 
  they automatically become admin in it).
* As an admin/sysadmin I want to be able to add/remove users from an 
  organisation/group and specify the role of that user (admin/editor).		1
* As an admin of the organization I should be able to edit details about 
  the organization/group eg. name/description.
* As the catalog creator I want to provide a custom form for both 
  groups/organization.

Organizations Only
++++++++++++++++++

* As an editor/admin of an organisation, I want to be able to 
  edit/create/manage/view all datasets within it.  This includes the ablity 
  to set the dataset as public/private.
* As an editor/admin of an organisation any datasets that I create must 
  belong to one and only one organization.

Groups Only
+++++++++++

* As an editor/admin of a Group, I want to be able to add/remove datasets from
  the group (a dataset can belong to many groups)


User stories about how a user asks to be a member of a group/organization and 
how a person asks as for a new group/organization to be created have been 
explicitly missed out from this. This is because they can be added later and are very 
likely to be instance specific.


Technical FAQ
=============

**What is the data model for this groups/organization?**


The data model will not change from how it is currently::
  
                                           +------------+
                                           |            |
                                       +---+  dataset   |
    +------------+     +-----------+   |   |            |
    |            |     |           +---+   +------------+
    |  group     +-----+ member    |       
    |            |     |           +---+   +------------+
    +------------+     +-----------+   |   |            |
                                       +---+   user     |
                                           |            |
                                           +------------+

The group table has a "type" field specifying if the table is an "organization" 
or a "group".

The member table has field called capacity which should be used as follows: 

*  When a dataset is a member of an Organization it must have capacity of 
   either public/private.
*  When a dataset is a member of an Group it must have capacity of member.
*  When a user is a member of a Group/Organization it must have capacity 
   of admin/editor.


**What do we do about the case when we want the public to add datasets?**

A config setting should be added so that a "public" group is created and that 
all new users and datasets get added to that group, unless otherwise specified.


**What do we do about changing ownership of a dataset to a different organization?**

Only a sysadmin should be able to do this by default.  We could consider the 
case where the creator of the dataset can trasnfer ownership over to a different organization 
but this should be added as a customization/extension as will only be relevant for sites where the public
can edit.




