Organizations and Groups
========================

This file contains the essential use cases and user stories (but not all
possible use cases and user stories) for Organizations and Groups in CKAN. It
should give a sense of the purpose of these features and the difference between
Groups and Organizations. The file then gives some technical analysis of how
the features should be implemented.

Use Cases
---------

**A site like thedatahub.org**:
You want users to be able to register new user accounts and start adding
datasets as quickly and easily as possible. You don't want them to have to join
an organization before they can add a dataset, or to have to choose an
organization when adding a dataset. You would turn on the option that creates a
default 'public' organization that datasets are added to if no other
organization is specified.

**A site like data.gov.uk**:
They don't want just anyone to be able to register a user account and start
adding content. So you would turn off the default public organization, and new
users would have to be added to an organization by a sysadmin or organization
admin before they can start adding content. By having multiple organizations
with different admins, they can distribute the responsibility for giving users
permission to create content.

**If we have organizations, then what are groups for?**
The main difference between organizations and groups are:

1. A member of an organization can edit any of the datasets in that
   organization. Members of groups do not get permission to edit the group's
   datasets, only to add datasets to and remove datasets from the group.

2. A dataset must belong to exactly one organization, but can belong no group
   or to multiple groups.

Organizations are more about controlling who has permission to add and edit
datasets, whereas groups are just about categorizing datasets.

data.gov.uk or thedatahub.org could use groups if they wanted a way for the
public to organize datasets into categories, or if they wanted groups of people
to be able to create sets of data to work on collaboratively. For example at
hackdays people often start by putting relevant datasets into a group. With
groups, this kind of collaboration can be orthogonal to the authorization
around organizations.

**What is the difference between groups and tags?**
Groups work like controlled tags. While anyone who can edit a dataset can
create a new tag, only sysadmins can create new groups. While anyone can add
any tag to a dataset, only sysadmins or members of a group can add a dataset
to that group.


User Stories
------------

Roles for the User Stories
``````````````````````````

These roles are used to describe users in the user stories below:

**Sysadmin** - A CKAN sysadmin user.

**Organization or Group Editor** - A CKAN user who is a member of an
organization or group with capacity _editor_.

**Organization or Group Admin** - A CKAN user who is a member of an
organization or group with capacity _admin_.

**User** - A CKAN user who is not a member of any particular organization
or group on the site.

**Anyone** - Anyone in any of the above roles, or even a site visitor who is
not even logged in.

User Stories that apply to both Organizations and Groups
````````````````````````````````````````````````````````

* **Anyone** can see a list of all the site's organizations.
* **Anyone** can see a list of all the site's groups.
* **Anyone** can see a list of all an organization's _public_ datasets
* **Anyone** can see a list of all a group's datasets (groups can't have
  private datasets, they're all public)
* **Sysadmins** can create new organizations, and automatically become admins
  of the organizations they create.
* **Sysadmins** can create new groups, and automatically becomes admins of the
  groups they create.
* **Users** can create new organizations, if this is enabled in the config
  file (boolean option), and will automatically become admin of the new
  organization
* **Users** can create new groups, if this is enabled in the config
  file (another boolean option), and will automatically become admin of the new
  group
* **Organization admins** can add users to and remove users from an
  organization that they are admin of.
* **Organization admins** can specify what role (editor or admin) each user who
  is a member of the organization has.
* **Group admins** can add users to and remove users from a group that they
  are admin of.
* **Group admins** can add specify what role (editor or admin) each
  user who is a member of the group has.
* **Sysadmins** can add users to and remove users from any organization or
  group, and set the role (editor or admin) of any user in any organization or
  group.
* **Organization admins** and **sysadmins** can edit the organization's
  metadata (name, description, etc.)
* **Group admins** and **sysadmins** can edit the group's metadata (name,
  description, etc.)
* **Developers** can provide custom forms for groups and organizations, for
  example to add custom metadata fields to groups or organizations.
* **Anyone** can see which users are members of groups.
* **Sysadmins** should decide if members of organizations should be visible to the public
  globally throughout the site.  If they are not visible to the public only syadmins and
  orgainization admins should be able to see the members of the organization.


User Stories that apply to Organizations Only
`````````````````````````````````````````````

* **Organization admins and editors** can see an organization's private
  datasets. They should be able to see them in thier organization's search
  results and have a facet of public/private so they can filter by them.
* **Organization admins and editors** can create new datasets that belong to
  the organization, and choose whether they are public or private.
* **Organization admins and editors** can edit all datasets belonging to the
  organization, including making the datasets public or private.
* **Organization admins and editors** can _only_ create datasets that belong to
  one of the organizations they are a member of. They cannot create a dataset
  that doesn't belong to any organization, and a dataset cannot belong to more
  than one organization at a time.

This last use story raises the question of whether it's possible for anyone to
create a dataset that doesnt belong to any organization, or whether everyone
has to join an organization before they can start adding datasets.

The suggestion solution is a boolean config option that, if enabled, creates a
default 'public' organization that new datasets are added to if no other
organization is specified. Users who are not a member of an organization will
be able to add datasets to this default organization.

* **Sysadmins** can move datasets from one organization to another.

* **Sysadmins** can delete organizations, and this deletes all of the
  organization's datasets.

User Stories that apply to Groups Only
``````````````````````````````````````

* **Group editors and admins** can add datasets to and remove datasets from the
  groups that they are members of. A dataset can belong to multiple groups at
  once, or can belong to no groups.

* **Sysadmins and Group Admins** can delete groups, but unlike with organizations this does not
  delete the group's datasets.

Joining Groups and Organizations
````````````````````````````````

User stories about how users can apply to join groups and organizations or can
request the creation of groups and organizations have been intentionally left
out. These user stories can be added later and are very likely to be instance
specific. (But note that by default according to the user stories above
sysadmins and, if enabled, normal users can create organizations and groups,
and sysadmins and organization and group admins can add users to organizations
and groups.)

Hierarchies of Groups and Organizations
```````````````````````````````````````

Previous specifications and implementations of organizations supported
hierarchies in which organizations could be parents and children of each other.
We do not intend to support this in the new implementation, at least not at
first.

Private Groups and Organizations
````````````````````````````````

Although we will support private datasets in organizations, we do not intend to
support private organizations or groups that cannot be seen by everyone, at
least not at first.

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

Using the one 'group' table for both organizations and groups means you can't
have an organization and a group with the same name. This is probably a good
thing as it would be confusing for users anyway.

The member table has field called capacity which should be used as follows:

*  When a dataset is a member of an Organization it must have capacity of
   'ozganization'.
*  When a dataset is a member of a Group it must have capacity of 'member'.
*  When a user is a member of a Group/Organization it must have capacity
   of the users role eg. admin, editor, memeber


The package table has gained two new fields

owner_org - the id of the owning organization
private - determines if the dataset is public or private
`
Config options
==============

The following config options have been created.

ckan.auth.user_create_organizations
ckan.auth.user_create_groups

ckan.auth.create_user_via_api
ckan.auth.create_dataset_if_not_in_organization

ckan.auth.anon_create_dataset
ckan.auth.user_delete_groups

ckan.auth.user_delete_organizations
ckan.auth.create_unowned_dataset
