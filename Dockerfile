FROM phusion/baseimage:0.9.13
MAINTAINER Open Knowledge

# Disable SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

ENV HOME /root
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CKAN_DATA /var/lib/ckan
ENV CKAN_DATAPUSHER_HOME /usr/lib/ckan/datapusher

# Customize postgres user/pass/db
ENV POSTGRESQL_USER ckan
ENV POSTGRESQL_PASS ckan
ENV POSTGRESQL_DB ckan

# Customize datastore user/pass/db
ENV POSTGRESQL_DATASTORE_USER datastore
ENV POSTGRESQL_DATASTORE_PASS datastore
ENV POSTGRESQL_DATASTORE_DB datastore

# Install required packages
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get -qq -y install \
        python-minimal \
        python-dev \
        python-virtualenv \
        libevent-dev \
        libpq-dev \
        nginx-light \
        apache2 \
        libapache2-mod-wsgi \
        postfix \
        build-essential \
        git \
        postgresql-client \
        libxml2-dev \
        libxslt1-dev \
        libgeos-c1

# Install CKAN
RUN virtualenv $CKAN_HOME
RUN mkdir -p $CKAN_HOME $CKAN_CONFIG $CKAN_DATA
RUN chown www-data:www-data $CKAN_DATA

ADD ./requirements.txt $CKAN_HOME/src/ckan/requirements.txt
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
ADD . $CKAN_HOME/src/ckan/
RUN $CKAN_HOME/bin/pip install -e $CKAN_HOME/src/ckan/
RUN ln -s $CKAN_HOME/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini

# Install CKAN Plugins that have no dependencies
# pages
RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-pages.git#egg=ckanext-pages
# viewhelpers
RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-viewhelpers.git#egg=ckanext-viewhelpers
RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-basiccharts.git#egg=ckanext-basiccharts
RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-dashboard.git#egg=ckanext-dashboard
RUN $CKAN_HOME/bin/pip install -e git+https://github.com/ckan/ckanext-mapviews.git#egg=ckanext-mapviews

# Install CKAN Datapusher
RUN virtualenv $CKAN_DATAPUSHER_HOME
RUN $CKAN_DATAPUSHER_HOME/bin/pip install -e git+https://github.com/ckan/datapusher.git#egg=datapusher
RUN $CKAN_DATAPUSHER_HOME/bin/pip install -r $CKAN_DATAPUSHER_HOME/src/datapusher/requirements.txt

# Configure apache
RUN a2dissite 000-default
RUN a2enmod wsgi
## ckan configuration
ADD ./contrib/docker/apache.wsgi $CKAN_CONFIG/apache.wsgi
ADD ./contrib/docker/apache.conf /etc/apache2/sites-available/ckan_default.conf
RUN echo "Listen 8080" > /etc/apache2/ports.conf
RUN a2ensite ckan_default
## datapusher configuration
ADD ./contrib/docker/datapusher.wsgi /etc/ckan/datapusher.wsgi
ADD ./contrib/docker/datapusher_settings.py /etc/ckan/datapusher_settings.py
ADD ./contrib/docker/datapusher.conf /etc/apache2/sites-available/datapusher.conf
RUN echo "Listen 8800" >> /etc/apache2/ports.conf
RUN a2ensite datapusher

# Configure nginx
ADD ./contrib/docker/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /var/cache/nginx

# Configure postfix
ADD ./contrib/docker/main.cf /etc/postfix/main.cf

# Configure runit
ADD ./contrib/docker/my_init.d /etc/my_init.d
ADD ./contrib/docker/svc /etc/service
CMD ["/sbin/my_init"]

VOLUME ["/var/lib/ckan", "/usr/lib/ckan/default", "/etc/ckan/default", "/var/log"]
EXPOSE 80 8800

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
