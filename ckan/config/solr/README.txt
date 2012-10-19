CKAN SOLR schemas
=================

This folder contains the latest and previous versions of the SOLR XML
schema files used by CKAN. These can be use on the SOLR server to
override the default SOLR schema. Please note that not all schemas are 
backwards compatible with old CKAN versions. Check the CHANGELOG.txt file
in this same folder to check which version of the schema should you use
depending on the CKAN version you are using.

Developers, when pushing changes to the SOLR schema:

* Note that updates on the schema are only release based, i.e. all changes
  in the schema between releases will be part of the same new version of
  the schema.

* Name the new version of the file using the following convention::
    
    schema-<version>.xml

* Update the `version` attribute of the `schema` tag in the new file::

    <schema name="ckan" version="<version>">

* Update the SUPPORTED_SCHEMA_VERSIONS list in `ckan/lib/search/__init__.py`
  Consider if the changes introduced are or are not compatible with
  previous schema versions.

* Update the CHANGELOG.txt file with the new version, the CKAN version
  required and changes made to the schema.
