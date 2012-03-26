========
Resource
========

A Resource corresponds to a file, API or other online data resource. A Resource
is associated to a :doc:`domain-model-dataset` (which may have several Resources).

Attributes
==========

Like Datasets, Resources can have arbitrary set of attributes. Thus, the
attributes listed here are not exhaustive and may be extended by specific
extensions.

Standard
--------

These are standard set of attributes utilized by 'core' CKAN.

* url: the key attribute of a resource (and the only required attribute). The
  url points to the location online where the content of that resource can be
  found. For a file this would be the location online of that file (or more
  generally a url which yields the bitstream representing the contents of that
  file -- for example some "files" are only generated on demand from a
  database). For an API this would be the endpoint for the api.
* name: a name for this resource (could be used in a ckan url)
* description: A brief description (one sentence) of the Resource. Longer
  descriptions can go in notes field of the associated Data Package.
* type: the type of the resource. One of: file | file.upload | api |
  visualization | code | documentation

  * file - a file (GET of this url should yield a bitstream)
  * file.upload - a file uploaded to the :doc:`filestore`
  * api - an API
  * visualization - a visualization
  * code - code related to this dataset (for example a reference to a code
    repository containing processing scripts)
  * documentation - documentation for this dataset

* format: human created format string with possible nesting e.g. zip:csv. See
  below for details of the format field.
* mimetype: standard mimetype (e.g. for zipped csv would be application/zip)
* mimetype-inner: mimetype of innermost object (so for example would be
  text/csv)
* size: size of the resource (content length). Usually only relevant for
  resources of type file.
* last_modified: the date when this resource's data was last modified (NB:
  *not* the date when the metadata was modified).
* hash: md5 or sha-1 hash

Resource Quality Information
----------------------------

See http://wiki.ckan.org/Data_Quality. This information, while directly related
resources, will not be stored on the resource table. It is currently undecided
whether the Resource object will have this data directly available (e.g. via a
'quality' attribute).

Attributes for FileStore Archiving and DataStore Usage
------------------------------------------------------

Resource data may have been archived into the FileStore or stored into the
DataStore. In these cases the following additional attributes are used:

* cache_url: url for cache of object in :doc:`filestore`

  * Note could be same as resource url if resource directly stored in storage

* cache_last_updated: timestamp when cached version was created

* webstore_url: set to non-empty value if data is in the doc:`datastore` (note
  unusual naming is a holdover from previous usage)
* webstore_last_updated: timestamp when webstore was last updated

Resource Format Strings
=======================

Conventions on format strings:

* file: mime-type or file extensions (for common tile types)

  * Examples: csv (text/csv), xls (application/vnd.ms-excel or application/xls
    -- there are about 6 alternatives!), html (text/html), pdf
    (application/pdf) etc

* api: {spec-type}+{mime-type-of-standard-response}

  * Examples: sparql+rdf/xml, rest+json

* service: service/{service-identifier}/{type-of-object-or-file-format}

  * Examples: service/gdocs/spreadsheet (google docs spreadsheet)

Nested Formats
--------------

It is very common for files to be provided in compressed form (e.g. zip, targz,
tar). Strictly the format of this object is the format for the compression
(e.g. zip). However, for users it is the underlying format that will matter. To
solve this one provides the formats in nested order separate by a colon.
Formats should be provide in outermost first (i.e. start with format of last
layer and work inwards). Examples:

* zip:json - a zipped json file e.g. myfile.json.zip 
* targz:xml - an xml file that has been tar'd and gzipped e.g. myfile.xml.tgz
* torrent:zip:csv - a csv file that has been zipped and then provided as a torrent

Multiple Formats for Same Resources
-----------------------------------

It is common for a given API to provide data in multiple formats, for example
xml and json. In this case use the '||' term. Examples:

* api/xml||json - an API providing both xml and json

Formats for resources that are listings or index pages
------------------------------------------------------

It is common, at present, to find projects where the data is in lots of files
with these files listed on an index page. Rather than attempt to create a
resource entry for each file we have adopted the convention of creating a
resource for the relevant index page with a special format string beginning
"index", e.g.:

* index/html (an index page in html format)
* index/ftp (an index page for a ftp site)

