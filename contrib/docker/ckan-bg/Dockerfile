# See CKAN docs on installation from Docker Compose on usage
FROM debian:stretch
MAINTAINER Marsdd

# Install required system packages
RUN apt-get -q -y update \
  && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
  && apt-get -q -y install \
  python-dev \
  python-pip \
  python-virtualenv \
  python-wheel \
  libpq-dev \
  libxml2-dev \
  libxslt-dev \
  libgeos-dev \
  libssl-dev \
  libffi-dev \
  postgresql-client \
  build-essential \
  git-core \
  vim \
  wget \
  curl \
  && apt-get -q clean \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y redis-tools

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

# Build-time variables specified by docker-compose.yml / .env
ARG CKAN_SITE_URL

# Create ckan user
RUN useradd -r -u 900 -m -c "ckan account" -d $CKAN_HOME -s /bin/false ckan

# Setup virtual environment for CKAN
RUN mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH && \
  virtualenv $CKAN_VENV && \
  ln -s $CKAN_VENV/bin/pip /usr/local/bin/ckan-pip &&\
  ln -s $CKAN_VENV/bin/paster /usr/local/bin/ckan-paster &&\
  ckan-pip install -e git+https://github.com/ckan/ckanext-googleanalytics.git#egg=ckanext-googleanalytics && \
  ckan-pip install -r $CKAN_VENV/src/ckanext-googleanalytics/requirements.txt

# Setup CKAN
ADD . $CKAN_VENV/src/ckan/
RUN ckan-pip install -U pip && \
  ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
  ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt && \
  ckan-pip install -e $CKAN_VENV/src/ckan/ && \
  ckan-pip install -e git+https://github.com/marsdd/ckanext-marsavin.git#egg=ckanext-marsavin && \
  ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
  cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-bg/ckan-entrypoint.sh /ckan-entrypoint.sh && \
  chmod +x /ckan-entrypoint.sh && \
  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan

CMD ["/usr/lib/ckan/venv/bin/paster","--plugin=ckan","jobs","worker","--config=/etc/ckan/production.ini"]
