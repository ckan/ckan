# See CKAN docs on installation from Docker Compose on usage
FROM python:3.7-stretch
MAINTAINER Open Knowledge

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        libgeos-dev \
        libssl-dev \
        libffi-dev \
        postgresql-client \
        build-essential \
        git-core \
        vim nano \
        nginx supervisor \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -U pip && pip install --upgrade --no-cache-dir uwsgi

# Define environment variables
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_INST $CKAN_HOME/installation
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH=/var/lib/ckan

# Build-time variables specified by docker-compose.yml / .env
ARG CKAN_SITE_URL

# Create ckan user
RUN useradd -r -u 900 -m -c "ckan account" -d $CKAN_HOME -s /bin/false ckan

# Setup virtual environment for CKAN
RUN mkdir -p $CKAN_INST $CKAN_CONFIG $CKAN_STORAGE_PATH


# Install Requirements before the CKAN code, as they change at a much slower rate.
# This way we don't re-fetch the requirements when chaning a single line of code
ADD ./requirement-setuptools.txt /tmp
ADD ./requirements.txt /tmp

RUN pip install --upgrade --no-cache-dir -r /tmp/requirement-setuptools.txt && \
    pip install --upgrade --no-cache-dir -r /tmp/requirements.txt

# Setup CKAN
ADD . $CKAN_INST/src/ckan/
ADD ./contrib/docker/ckan-entrypoint.sh  /
RUN pip install -e $CKAN_INST/src/ckan/ && \
    ln -s $CKAN_INST/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
    chmod +x /ckan-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_INST $CKAN_CONFIG $CKAN_STORAGE_PATH


# Setup the WSGI server
ADD contrib/docker/nginx.conf /etc/nginx/sites-available/ckan
RUN rm  /etc/nginx/sites-enabled/default && \
  ln -s /etc/nginx/sites-available/ckan /etc/nginx/sites-enabled/ckan
ADD wsgi.py /etc/ckan/
ADD ckan-uwsgi.ini /etc/c/usr/lib/ckan/installation/src/ckan/binkan/
ADD contrib/docker/ckan-uwsgi.conf /etc/supervisor/conf.d/

ENTRYPOINT ["/ckan-entrypoint.sh"]


EXPOSE 5000

CMD ["ckan","-c","/etc/ckan/production.ini", "run", "--host", "0.0.0.0"]
