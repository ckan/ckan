================
Tag Vocabularies
================

.. versionadded:: 1.7

CKAN sites can have *tag vocabularies*, which are a way of grouping related
tags together into custom fields.

For example, if you were making a site for music datasets. you might use a tag
vocabulary to add two fields *Genre* and *Composer* to your site's datasets,
where each dataset can have one of the values *Avant-Garde*, *Country* or
*Jazz* in its genre field, and one of the values *Beethoven*, *Wagner*, or
*Tchaikovsky* in its composer field. In this example, genre and composer would
be vocabularies and the values would be tags:

- Vocabulary: Genre

  - Tag: Avant-Garde

  - Tag: Country

  - Tag: Jazz

- Vocabulary: Composer

  - Tag: Beethoven

  - Tag: Wagner

  - Tag: Tchaikovsky

Ofcourse, you could just add Avant-Garde, Beethoven, etc. to datasets as normal
CKAN tags, but using tag vocabularies lets you define Avant-Garde, Country and
Jazz as genres and Beethoven, Wagner and Tchaikovsky as composers, and lets you
enforce restrictions such as that each dataset must have a genre and a
composer, and that no dataset can have two genres or two composers, etc.

Another example use-case for tag vocabularies would be to add a *Country Code*
field to datasets defining the geographical coverage of the dataset, where each
dataset is assigned a country code such as *en*, *fr*, *de*, etc. See
``ckanext/example_idatasetform`` for a working example implementation of
country codes as a tag vocabulary.


Properties of Tag Vocabularies
------------------------------

* A CKAN website can have any number of vocabularies.
* Each vocabulary has an ID and name.
* Each tag either belongs to a vocabulary, or can be a *free tag* that doesn't
  belong to any vocabulary (i.e. a normal CKAN tag).
* A dataset can have more than one tag from the same vocabulary, and can have tags from more than one vocabulary.

Using Vocabularies
------------------

To add a tag vocabulary to a site, a CKAN sysadmin must:

1. Call the ``vocabulary_create()`` action of the CKAN API to create the
   vocabulary and tags. See :doc:`api`.

2. Implement an ``IDatasetForm`` plugin to add a new field for the tag
   vocabulary to the dataset schema. See :doc:`extensions/index`.

3. Provide custom dataset templates to display the new field to users when
   adding, updating or viewing datasets in the CKAN web interface.
   See :doc:`theming`.

See ``ckanext/example_idatasetform`` for a working example of these steps.
