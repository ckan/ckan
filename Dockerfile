# See CKAN docs on installation from Docker Compose on usage
FROM debian:stretch
MAINTAINER Open Knowledge

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        python-dev \
        python-pip \
        python-virtualenv \
        python-wheel \
        python3-dev \
        python3-pip \
        python3-virtualenv \
        python3-wheel \
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
        python-factory-boy \
        python-mock \
        supervisor \
        cron \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*

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
    ln -s $CKAN_VENV/bin/ckan /usr/local/bin/ckan

# Setup CKAN
ADD . $CKAN_VENV/src/ckan/
COPY ./contrib/docker/production.ini $CKAN_CONFIG/production.ini
COPY ./contrib/docker/who.ini $CKAN_VENV/src/ckan/ckan/config/who.ini
RUN ckan-pip install -U pip && \
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements-py2.txt && \
    ckan-pip install -e $CKAN_VENV/src/ckan/ && \
    ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
    cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh && \
    chmod +x /ckan-entrypoint.sh && \
    cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-harvester-entrypoint.sh /ckan-harvester-entrypoint.sh && \
    chmod +x /ckan-harvester-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

# Install needed libraries
RUN ckan-pip install factory_boy
RUN ckan-pip install mock


WORKDIR $CKAN_VENV/src
COPY ./contrib/docker/src/ckanext-harvest $CKAN_VENV/src/ckanext-harvest
COPY ./contrib/docker/src/ckanext-spatial $CKAN_VENV/src/ckanext-spatial
COPY ./contrib/docker/src/ckanext-cioos_theme $CKAN_VENV/src/ckanext-cioos_theme
RUN  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH


RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-harvest/pip-requirements.txt"
RUN chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-harvest && python setup.py install && python setup.py develop"

RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-spatial/pip-requirements.txt"
RUN chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-spatial && python setup.py install && python setup.py develop"

RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-cioos_theme && python setup.py install && python setup.py develop"

RUN  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

COPY ./contrib/docker/ckan_harvesting.conf /etc/supervisor/conf.d/ckan_harvesting.conf
RUN  mkdir /var/log/ckan && mkdir /var/log/ckan/std

# setup harvesting cron job
#COPY ./contrib/docker/crontab /etc/cron.d/ckan_harvesting
#RUN chmod 0644 /etc/cron.d/ckan_harvesting

COPY ./contrib/docker/crontab  /var/spool/cron/crontabs/root
RUN chmod 0600 /var/spool/cron/crontabs/root


ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan
EXPOSE 5000

CMD ["ckan","-c","/etc/ckan/production.ini", "run", "--host", "0.0.0.0"]
