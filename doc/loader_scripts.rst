==============
Loader scripts
==============

Introduction
============

'Loader scripts' provide a simple way to take any format metadata and bulk upload it to a remote CKAN instance. Essentially each custom script has to convert the metadata to the standard 'package' dictionary format, and the loader does the work of loading it into CKAN in an intelligent way.


Structure
=========

First you need an importer that derives from `PackageImporter` (ckan/lib/importer.py). This takes whatever format the metadata is in and sorts it into records of type `DataRecord`. Then each DataRecord is converted into the correct fields for a package using the `record_2_package` method. This results in package dictionaries.

Note: for CSV and Excel formats, there is already the `SpreadsheetPackageImporter` (ckan/lib/spreadsheet_importer.py) which wraps the file in `SpreadsheetData` before extracting the records into `SpreadsheetDataRecords`.

The `PackageLoader` takes the package dictionaries and loads them onto a CKAN instance using the ckanclient. There are various settings to determine:
 * how to identify the same package, previously been loaded into CKAN. This canbe simply by name or by an identifier stored in another field.
 * how to merge in changes to an existing packages. It can simply replace it or maybe merge in resources etc.

Loaders generally go into the `ckanext` repository.

The loader shoud be given a command line interface using the `Command` base class (ckanext/command.py). You need to add a line to the setup.py `[console_scripts]` and when you run ``python setup.py develop`` it creates a script for you in your python environment.


Example
=======

To get a flavour of what these scripts look like, take a look at the ONS scripts: https://bitbucket.org/okfn/ckanext-dgu/src/default/ckanext/dgu/ons/

