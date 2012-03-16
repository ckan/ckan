=======
Dataset
=======

A Dataset (known as a (Data) Package in CKAN <=1.4) is the object representing
datasets in CKAN and, as such, is the central domain object.

When you retrieve a Dataset in the CKAN API it will automatically include
information from most related objects including Tags, Resources, Relationships,
Ratings etc.

Schema
======

Mappings to dublin core are in brackets (dc:...).

* id: unique id
* name (slug): unique name that is used in urls and for identification
* title (dc:title): short title for dataset
* url (home page): home page for this dataset
* author (dc:creator): original creator of the dataset
* author_email: 
* maintainer: current maintainer or publisher of the dataset
* maintainer_email:
* license (dc:rights): license under which the dataset is made available
* version: dataset version
* notes (description) (dc:description): description and other information about the dataset
* tags: arbitrary textual tags for the dataset
* state: state of dataset in CKAN system (active, deleted, pending)
* resources: list of [[Domain Model/Resource|Resources]]
* groups: list of [[Domain Model/Group|Groups]] this dataset is a member of
* "extras" - arbitrary, unlimited additional key/value fields

The schema in code (see default_package_schema):
https://github.com/okfn/ckan/blob/master/ckan/logic/schema.py

Background
==========

The CKAN Dataset was originally heavily based on the kind of packaging
information provided for software but with some modifications. One of our aims
is to keep things simple and as generic as possible as we have data from a lot
of different domains.

Thus we've tried to keep the core metadata pretty restricted but allow for
additional info either via tags or via "extra" arbitrary key/value fields.

