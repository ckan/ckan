===================
Publishing Datasets
===================

.. note: CKAN instances will often have a custom publishing workflow.
         The tutorial presented here assumes the standard (default) workflow.


Datasets and resources
======================

CKAN organizes data using the concepts of *datasets* and *resources*.

Dataset
    A dataset is the primary object - a "set of data".
    Datasets contain resources.

Resource
    A resource represents individual data items in a dataset.
    For example: a ``csv`` file, the URL of an API, etc.

Both datasets and resources can have information (metadata) associated with
them.

Although datasets may contain any number of resources, they will generally
consist of a relatively small number of resources that are grouped together
because the resource content is similar in some way.
For example, a dataset may contain multiple resources
that represent the same underlying data in different formats
(for example: ``csv`` and ``xls`` files).


Storing data in CKAN and external resources
===========================================

A CKAN resource may be simply a URL that links to a data item that resides on a
different server (for example: a link to an online ``csv`` file).
These resources are said to be *external* as they are not actually part of
the CKAN site.
The data can be changed without any update to the CKAN resource.

Data can also be stored directly in a CKAN site. There are two ways to do this:

1. Using the `FileStore <filestore.html>`_.
2. Using the `DataStore <datastore.html>`_.


Publishing a dataset: a brief tutorial
======================================


* Select some data to use.
  For the purposes of this tutorial you will want to have some data to publish
  on a CKAN site. If you don't have any, we suggest that you just use some
  of the raw data from this `Gold Prices dataset`_ on the DataHub.
* Log in to the CKAN site (or sign up if you don't have an account yet).
* Click on "Datasets" in the menu at the top.
* Click on "Add Dataset" at the top right (below the search box).
* Fill in the fields in the form and click "Next: Add Data".
* Add a link to your data or upload a file. More than one resource can be
  added by clicking "Save & add another". When you are finished adding
  resources, click "Next: Additional Info".
* Add any additional information that you have and then click "Finish".

You should now be redirected to the page for your new dataset. You can come
back and edit this dataset at any time.

.. _Gold Prices Dataset: http://datahub.io/dataset/gold-prices
