# See CKAN docs on installation from Docker Compose on usage
#------------------------------------------------------------------------------#
FROM debian:stretch as base
#------------------------------------------------------------------------------#
MAINTAINER Open Knowledge

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        python-dev \
        python-pip \
        python-virtualenv \
        python-wheel \
        python-lxml \
        python-owslib \
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

RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal
RUN export C_INCLUDE_PATH=/usr/include/gdal

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
ADD ./bin/ $CKAN_VENV/src/ckan/bin/
ADD ./ckan/ $CKAN_VENV/src/ckan/ckan/
ADD ./ckanext/ $CKAN_VENV/src/ckan/ckanext/
ADD ./scripts/ $CKAN_VENV/src/ckan/scripts/
COPY ./*.py ./*.txt ./*.ini ./*.rst $CKAN_VENV/src/ckan/
ADD ./contrib/docker/production.ini $CKAN_CONFIG/production.ini
ADD ./contrib/docker/who.ini $CKAN_VENV/src/ckan/ckan/config/who.ini
ADD ./contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh
ADD ./contrib/docker/ckan-harvester-entrypoint.sh /ckan-harvester-entrypoint.sh
ADD ./contrib/docker/ckan-run-harvester-entrypoint.sh /ckan-run-harvester-entrypoint.sh
ADD ./contrib/docker/crontab $CKAN_VENV/src/ckan/contrib/docker/crontab

RUN ckan-pip install -U pip && \
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
    ckan-pip install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements-py2.txt && \
    ckan-pip install -e $CKAN_VENV/src/ckan/ && \
    ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \
    chmod +x /ckan-entrypoint.sh && \
    chmod +x /ckan-harvester-entrypoint.sh && \
    chmod +x /ckan-run-harvester-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH


# Install needed libraries
RUN ckan-pip install factory_boy
RUN ckan-pip install mock
RUN ckan-pip install urllib3
RUN ckan-pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==2.1.0

# for debugging
RUN ckan-pip install flask_debugtoolbar

# Copy extensions into container and Install
WORKDIR $CKAN_VENV/src
COPY ./contrib/docker/src/pycsw $CKAN_VENV/src/pycsw
COPY ./contrib/docker/pycsw/pycsw.cfg $CKAN_VENV/src/pycsw/default.cfg
COPY ./contrib/docker/src/ckanext-harvest $CKAN_VENV/src/ckanext-harvest
COPY ./contrib/docker/src/ckanext-spatial $CKAN_VENV/src/ckanext-spatial
COPY ./contrib/docker/src/ckanext-cioos_theme $CKAN_VENV/src/ckanext-cioos_theme
COPY ./contrib/docker/src/ckanext-cioos_harvest $CKAN_VENV/src/ckanext-cioos_harvest
COPY ./contrib/docker/src/ckanext-scheming $CKAN_VENV/src/ckanext-scheming
COPY ./contrib/docker/src/ckanext-composite $CKAN_VENV/src/ckanext-composite
COPY ./contrib/docker/src/ckanext-repeating $CKAN_VENV/src/ckanext-repeating
COPY ./contrib/docker/src/ckanext_fluent $CKAN_VENV/src/ckanext_fluent
COPY ./contrib/docker/src/ckanext-package_converter $CKAN_VENV/src/ckanext-package_converter
RUN  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

COPY ./contrib/docker/src/ckanext-geoview/pip-requirements.txt $CKAN_VENV/src/ckanext-geoview/pip-requirements.txt
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-geoview/pip-requirements.txt"

COPY ./contrib/docker/src/ckanext-dcat/requirements.txt $CKAN_VENV/src/ckanext-dcat/requirements.txt
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-dcat/requirements.txt"

COPY ./contrib/docker/src/ckanext-harvest/pip-requirements.txt $CKAN_VENV/src/ckanext-harvest/pip-requirements.txt
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-harvest/pip-requirements.txt"

COPY ./contrib/docker/src/ckanext-spatial/requirements.txt $CKAN_VENV/src/ckanext-spatial/requirements.txt
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-spatial/requirements.txt"

# COPY ./contrib/docker/src/ckanext-scheming/requirements.txt $CKAN_VENV/src/ckanext-scheming/requirements.txt
# RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-scheming/requirements.txt"

COPY ./contrib/docker/src/ckanext-cioos_theme/dev-requirements.txt $CKAN_VENV/src/ckanext-cioos_theme/dev-requirements.txt
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-cioos_theme/dev-requirements.txt"

#------------------------------------------------------------------------------#
FROM base as extensions1
#------------------------------------------------------------------------------#
WORKDIR $CKAN_VENV/src

# COPY ./contrib/docker/src/pycsw $CKAN_VENV/src/pycsw
# COPY ./contrib/docker/pycsw/pycsw.cfg $CKAN_VENV/src/pycsw/default.cfg

COPY ./contrib/docker/src/ckanext-googleanalyticsbasic $CKAN_VENV/src/ckanext-googleanalyticsbasic
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-googleanalyticsbasic && python setup.py install && python setup.py develop"

COPY ./contrib/docker/src/ckanext-geoview $CKAN_VENV/src/ckanext-geoview
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-geoview && python setup.py install && python setup.py develop"

COPY ./contrib/docker/src/ckanext-dcat $CKAN_VENV/src/ckanext-dcat
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-dcat && python setup.py install && python setup.py develop"

WORKDIR $CKAN_VENV/src
RUN /bin/bash -c "rm -R ./ckan"

WORKDIR $CKAN_VENV/lib/python2.7/site-packages/
RUN /bin/bash -c "find . -maxdepth 1 ! -name 'ckanext*' ! -name '..' ! -name '.' ! -name 'easy-install.pth' | xargs rm -R; mv easy-install.pth easy-install-A.pth"

#------------------------------------------------------------------------------#
FROM base as extensions2
#------------------------------------------------------------------------------#
WORKDIR $CKAN_VENV/src

COPY ./contrib/docker/src/ckanext-scheming $CKAN_VENV/src/ckanext-scheming
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-scheming && python setup.py install && python setup.py develop"

COPY ./contrib/docker/src/ckanext-fluent $CKAN_VENV/src/ckanext-fluent
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-fluent && python setup.py install && python setup.py develop"

COPY ./contrib/docker/src/ckanext-repeating $CKAN_VENV/src/ckanext-repeating
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-repeating && python setup.py install && python setup.py develop"

COPY ./contrib/docker/src/ckanext-composite $CKAN_VENV/src/ckanext-composite
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-composite && python setup.py install && python setup.py develop"

RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-fluent && python setup.py install && python setup.py develop"

RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-package_converter/requirements.txt"
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src && ckan-pip install -r ckanext-package_converter/dev-requirements.txt"
RUN /bin/bash -c "source $CKAN_VENV/bin/activate && cd $CKAN_VENV/src/ckanext-package_converter && python setup.py install && python setup.py develop"

RUN mkdir -p $CKAN_VENV/src/logs
RUN touch "$CKAN_VENV/src/logs/ckan_access.log"
RUN touch "$CKAN_VENV/src/logs/ckan_default.log"

RUN  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan
EXPOSE 5000

CMD ["ckan","-c","/etc/ckan/production.ini", "run", "--host", "0.0.0.0"]
