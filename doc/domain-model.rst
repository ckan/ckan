=================
CKAN Domain Model
=================

Overview
========

* **Datasets**: the central entity in CKAN. Associated to Datasets are 'Resources' (files,
  APIs etc) and a large variety of metadata. 
  
  * **Core metadata**: Datasets have a set of "core" metadata attributes
  * **Unlimited additional metadata**: Datasets may have an unlimited amount of
    arbitrary additional metadata in the form of "extra" key/value
    associations.
  * **Relationships**: relationships between datasets (such as depends on,
    child of, derived from etc)

* **Resources**: the actual data or APIs associated to a dataset are entered
  into Resources.

Additionally:

* **Revisions**: All metadata in the CKAN system is *revisioned* -- i.e. all
  changes are recorded. This support reverting changes, viewing changes, and,
  perhaps most importantly going forward, the exchange of metadata changesets
  between different CKAN instances or CKAN and other catalogues. However, this
  is not a core part of the schema.
* **Task Status**: A key/value store used by CKAN Tasks (background processes).

Entity List
===========

* :doc:`domain-model-dataset`
* :doc:`domain-model-resource` - a file, API or other resource
* Group
* Dataset Relationship - a relationship between Data Datasets.
* Tag - tags can be applied to packages.
* Vocabulary - tags can belong to vocabularies.

Part of the domain model but not central:

* Revision - changes to the domain model
* :doc:`domain-model-task-status` - key/value information stored by CKAN Tasks

