# docker build . -t ckan --build-arg CKAN_SITE_URL=http://localhost:5000
# docker run -d -p 80:5000 --link db:db --link redis:redis --link solr:solr ckan

FROM debian:jessie
MAINTAINER Open Knowledge

# Install required packages
RUN apt-get -q -y update && apt-get -q -y upgrade && \
        DEBIAN_FRONTEND=noninteractive apt-get -q -y install \
		python-dev \
        python-pip \
        python-virtualenv \
        libpq-dev \
        git-core \
        postgresql-client \
	&& apt-get -q clean

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_VENV $CKAN_HOME/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CKAN_STORAGE_PATH /var/lib/ckan

# Build-time variables specified by docker-compose.yml / .env or
# docker build . -t ckan --build-arg CKAN_SITE_URL=http://localhost:5000
ARG CKAN_SITE_URL

# add ckan user which runs all the ckan related stuff
RUN useradd -r -u 900 -m -c "ckan account" -d $CKAN_HOME -s /bin/false ckan

# SetUp Virtual Environment CKAN
RUN mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH && \
    virtualenv $CKAN_VENV && \
    ln -s $CKAN_VENV/bin/pip /usr/local/bin/ckan-pip &&\
    ln -s $CKAN_VENV/bin/paster /usr/local/bin/ckan-paster

# SetUp CKAN
ADD . $CKAN_VENV/src/ckan/
RUN ckan-pip install --upgrade -r $CKAN_VENV/src/ckan/requirements.txt && \
    ckan-pip install -e $CKAN_VENV/src/ckan/ && \
    ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
    cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh && \
    chmod +x /ckan-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

ENTRYPOINT ["/ckan-entrypoint.sh"]

# Volumes
VOLUME ["/etc/ckan/default"]
VOLUME ["/var/lib/ckan"]

USER ckan
EXPOSE 5000

CMD ["ckan-paster","serve","/etc/ckan/default/ckan.ini"]

