CKAN Solr schema
================

This folder contains the Solr schema file used by CKAN (schema.xml).

Starting from 2.2 this is the only file that should be used by users and
modified by devs. The rest of files (schema-{version}.xml) are kept for
backwards compatibility purposes and should not be used, as they might be
removed in future versions.

When upgrading CKAN, always check the CHANGELOG on each release to see if
you need to update the schema file and reindex your datasets.
