=========
DataStore
=========

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accessible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

The installation and set-up of the DataStore in outlined in :doc:`datastore-setup`.

If you want to use the API and you are looking for the API documentation, go to :doc:`datastore-api`.

Relationship to FileStore
=========================

The DataStore is distinct but complementary to the FileStore (see
:doc:`filestore`). In contrast to the the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction, consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this file would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore, one would be able to access
individual spreadsheet rows via a simple web API, as well as being able to make
queries over the spreadsheet contents.


.. _datastorer:

DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or
uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the DataStore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at: https://github.com/okfn/ckanext-datastorer
