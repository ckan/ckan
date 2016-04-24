#!/bin/sh
SOLR_HOME=${SOLR_HOME:-/opt/solr}
SOLR_URL=${SOLR_HOST:-http://localhost:8983}
SOLR_CORE=${SOLR_CORE:-ckan}
SOLR_SCHEMA=${SOLR_SCHEMA:-$HOME/ckan/ckan/config/solr/schema.xml}

INSTANCE_DIR=$SOLR_HOME/example/solr/$SOLR_CORE
cp -R $SOLR_HOME/example/solr/collection1 $SOLR_HOME/example/solr/$SOLR_CORE
cp $SOLR_SCHEMA $SOLR_HOME/example/solr/$SOLR_CORE/conf

curl "$SOLR_URL/solr/admin/cores?action=CREATE&name=$SOLR_CORE&instanceDir=$INSTANCE_DIR"