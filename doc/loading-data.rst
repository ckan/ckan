=============
Load Datasets
=============

You can upload individual datasets through the CKAN front-end, but for importing datasets on masse, you have two choices: 

* :ref:`load-data-api`. You can use the `CKAN API <api.html>`_ to script import. To simplify matters, we offer provide standard loading scripts for Google Spreadsheets, CSV and Excel. 

*  :ref:`load-data-harvester`.  The `CKAN harvester extension <https://github.com/okfn/ckanext-harvest/>`_ provides web and command-line interfaces for larger import tasks. 

If you need advice on data import, `contact the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.  

.. note :: If loading your data requires scraping a web page regularly, you may find it best to write a scraper on `ScraperWiki <http://www.scraperwiki.com>`_ and combine this with either of the methods above. 

.. _load-data-api:

Import Data with the CKAN API
-----------------------------

You can use the `CKAN API <api.html>`_ to upload datasets directly into your CKAN instance.

The Simplest Approach - ckanclient
++++++++++++++++++++++++++++++++++

The most basic way to automate dataset loading is with a Python script using the `ckanclient library <http://pypi.python.org/pypi/ckanclient>`_. You will need to register for an API key first. 

You can install ckanclient with::

 pip install ckanclient

Here is an example script to register a new dataset::

  import ckanclient
  # Instantiate the CKAN client.
  ckan = ckanclient.CkanClient(api_key=my_api_key, base_location="http://myckaninstance.com/api")
  # Describe the dataset.
  dataset_entity = {
        'name': my_dataset_name,
        'url': my_dataset_url,
        'download_url': my_dataset_download_url,
        'tags': my_dataset_keywords,
        'notes': my_dataset_long_description,
  }
  # Register the dataset.
  ckan.package_register_post(dataset_entity)

Loader Scripts
++++++++++++++

'Loader scripts' provide a simple way to take any format metadata and bulk upload it to a remote CKAN instance.

Essentially each set of loader scripts converts the dataset metadata to the standard 'dataset' format, and then loads it into CKAN. 

To get a flavour of what loader scripts look like, take a look at `the ONS scripts <https://github.com/okfn/ckanext-dgu/tree/master/ckanext/dgu/ons>`_.

Loader Scripts for CSV and Excel
********************************

For CSV and Excel formats, the `SpreadsheetPackageImporter` (found in ``ckanext-importlib/ckanext/importlib/spreadsheet_importer.py``) loader script wraps the file in `SpreadsheetData` before extracting the records into `SpreadsheetDataRecords`.

SpreadsheetPackageImporter copes with multiple title rows, data on multiple sheets, dates. The loader can reload datasets based on a unique key column in the spreadsheet, choose unique names for datasets if there is a clash, add/merge new resources for existing datasets and manage dataset groups.

Loader Scripts for Google Spreadsheets
**************************************

The `SimpleGoogleSpreadsheetLoader` class (found in ``ckanclient.loaders.base``) simplifies the process of loading data from Google Spreadsheets (there is an additional dependency on the ``gdata`` Python package).

`This script <https://bitbucket.org/okfn/ckanext/src/default/bin/ckanload-italy-nexa>`_ has a simple example of loading data from Google Spreadsheets. 

Write Your Own Loader Script
****************************

## this needs work ##

First, you need an importer that derives from `PackageImporter` (found in ``ckan/lib/importer.py``). This takes whatever format the metadata is in and sorts it into records of type `DataRecord`. 

Next, each DataRecord is converted into the correct fields for a dataset using the `record_2_package` method. This results in dataset dictionaries.

The `PackageLoader` takes the dataset dictionaries and loads them onto a CKAN instance using the ckanclient. There are various settings to determine:

 * ##how to identify the same dataset, previously been loaded into CKAN.## This can be simply by name or by an identifier stored in another field.
 * how to merge in changes to an existing datasets. It can simply replace it or maybe merge in resources etc.

The loader should be given a command-line interface using the `Command` base class (``ckanext/command.py``). 

You need to add a line to the CKAN ``setup.py`` (under ``[console_scripts]``) and when you run ``python setup.py develop`` it creates a script for you in your Python environment.

.. _load-data-harvester:

Import Data with the Harvester Extension
----------------------------------------

The `CKAN harvester extension <https://github.com/okfn/ckanext-harvest/>`_ provides useful tools for more advanced data imports.

These include a command-line interface and a web user interface for running harvesting jobs. 

To use the harvester extension, create a class that implements the `harvester interface <https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/interfaces.py>` derived from the `base class of the harvester extension <https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/harvesters/base.py>`_.

For more information on working with extensions, see :doc:`extensions`.
