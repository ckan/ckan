# FROM solr:6.6.5
# FROM solr:6.6.6
FROM solr:8
MAINTAINER Open Knowledge

EXPOSE 8983

# Enviroment
ENV SOLR_CORE ckan
ENV SOLR_CONFIG_DIR="/opt/solr/server/solr/configsets"
ENV SOLR_SCHEMA_FILE="$SOLR_CONFIG_DIR/ckan/conf/managed-schema"

USER root

# Create a CKAN configset by copying the default one
RUN cp -R $SOLR_CONFIG_DIR/_default $SOLR_CONFIG_DIR/ckan

# Adding Files
ADD ./ckan/config/solr/schema.xml $SOLR_SCHEMA_FILE
RUN chmod 644 $SOLR_SCHEMA_FILE

# User
USER $SOLR_USER:$SOLR_USER

CMD ["sh", "-c", "solr-precreate ckan $SOLR_CONFIG_DIR/ckan"]
