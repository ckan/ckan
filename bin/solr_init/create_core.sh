#!/bin/sh

INSTANCE_DIR=$SOLR_HOME/example/solr/$CKAN_SOLR_CORE
cp -R $SOLR_HOME/example/solr/collection1 $SOLR_HOME/example/solr/$CKAN_SOLR_CORE
cp $CKAN_SOLR_SCHEMA $SOLR_HOME/example/solr/$CKAN_SOLR_CORE/conf

curl "http://localhost:8983/solr/admin/cores?action=CREATE&name=$CKAN_SOLR_CORE&instanceDir=$INSTANCE_DIR"