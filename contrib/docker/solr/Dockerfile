FROM ubuntu:14.04
MAINTAINER Open Knowledge

# Install Java
RUN apt-get -q -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y install default-jre-headless

# Install Solr
ENV SOLR_HOME /opt/solr/example/solr
ENV SOLR_VERSION 4.8.1
ENV SOLR solr-$SOLR_VERSION
RUN mkdir -p /opt/solr
ADD https://archive.apache.org/dist/lucene/solr/$SOLR_VERSION/$SOLR.tgz /opt/$SOLR.tgz
RUN tar zxf /opt/$SOLR.tgz -C /opt/solr --strip-components 1

# Install CKAN Solr core
RUN cp -R $SOLR_HOME/collection1/ $SOLR_HOME/ckan/
RUN echo name=ckan > $SOLR_HOME/ckan/core.properties
ADD schema.xml $SOLR_HOME/ckan/conf/schema.xml

EXPOSE 8983
WORKDIR /opt/solr/example
CMD ["java", "-jar", "start.jar"]
