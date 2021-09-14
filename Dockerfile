# See CKAN docs on installation from Docker Compose on usage
FROM ubuntu:focal-20210119
MAINTAINER Open Knowledge

# Set timezone
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Setting the locale
ENV LC_ALL=en_US.UTF-8       
RUN apt-get update
RUN apt-get install --no-install-recommends -y locales
RUN sed -i "/$LC_ALL/s/^# //g" /etc/locale.gen
RUN dpkg-reconfigure --frontend=noninteractive locales 
RUN update-locale LANG=${LC_ALL}

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        python3.8 \
        python3-dev \
        python3-pip \
        python3-venv \
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
        apache2 libapache2-mod-rpaf libapache2-mod-wsgi-py3 \
        vim \
        wget \
        curl \
        gettext \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*

# Build-time variables specified by docker-compose.yml / .env
ARG CKAN_DOMAIN
ARG CKAN_SITE_URL

# Define environment variables
ENV CKAN_DOMAIN ${CKAN_DOMAIN:-localhost}
ENV CKAN_SITE_URL ${CKAN_SITE_URL}
ENV CKAN_HOME /usr/lib/ckan
ENV CKAN_VENV $CKAN_HOME/venv
ENV CKAN_CONFIG /etc/ckan
ENV CKAN_STORAGE_PATH /var/lib/ckan
ENV APACHE_RUN_USER ckan
ENV APACHE_RUN_GROUP ckan

# Create ckan user
RUN useradd -r -u 900 -m -c "ckan account" -d $CKAN_HOME -s /bin/false ckan

# Setup virtual environment for CKAN
RUN mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH && \
    python3 -m venv $CKAN_VENV && \
    ln -s $CKAN_VENV/bin/pip3 /usr/local/bin/ckan-pip3 &&\
    ln -s $CKAN_VENV/bin/ckan /usr/local/bin/ckan

# Virtual environment binaries/scripts to be used first
ENV PATH=${CKAN_VENV}/bin:${PATH}  

# Setup CKAN
ADD . $CKAN_VENV/src/ckan/
RUN ckan-pip3 install -U pip && \
    ckan-pip3 install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirement-setuptools.txt && \
    ckan-pip3 install --upgrade --no-cache-dir -r $CKAN_VENV/src/ckan/requirements.txt && \
    ckan-pip3 install -e $CKAN_VENV/src/ckan/ && \
    ln -s $CKAN_VENV/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini && \    
    cp -v $CKAN_VENV/src/ckan/contrib/docker/ckan-entrypoint.sh /ckan-entrypoint.sh && \
    chmod +x /ckan-entrypoint.sh && \
    chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH

# Setup CKAN web frontend
RUN ln -s $CKAN_VENV/src/ckan/contrib/docker/apache.wsgi $CKAN_CONFIG/apache.wsgi && \
    envsubst '${CKAN_DOMAIN}${CKAN_CONFIG}${CKAN_HOME}${CKAN_VENV}' < $CKAN_VENV/src/ckan/contrib/docker/apache.conf > /etc/apache2/sites-available/ckan.conf && \
    echo '' > /etc/apache2/ports.conf && \
    chown -R ckan:ckan /etc/apache2 /var/run/apache2 /var/log/apache2 /var/cache/apache2

RUN a2ensite  ckan
RUN a2dissite 000-default

ENTRYPOINT ["/ckan-entrypoint.sh"]

USER ckan
EXPOSE 5000 8080

CMD ["ckan","-c","/etc/ckan/production.ini", "run", "--host", "0.0.0.0"]
