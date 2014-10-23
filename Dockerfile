FROM phusion/baseimage:0.9.15
MAINTAINER Open Knowledge

# set UTF-8 locale
RUN locale-gen en_US.UTF-8 && \
    echo 'LANG="en_US.UTF-8"' > /etc/default/locale

RUN apt-get -qq update

ENV HOME /root
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CONFIG_FILE ckan.ini
ENV CKAN_DATA /var/lib/ckan
ENV CKAN_DATAPUSHER_HOME /usr/lib/ckan/datapusher

# Install required packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq -y install \
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
        libxml2-dev \
        libxslt1-dev \
        libgeos-c1 \
        supervisor

# Install CKAN
RUN virtualenv $CKAN_HOME
RUN mkdir -p $CKAN_CONFIG $CKAN_DATA
RUN chown www-data:www-data $CKAN_DATA

ADD . $CKAN_HOME/src/ckan/
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
RUN $CKAN_HOME/bin/pip install -e $CKAN_HOME/src/ckan/
RUN ln -s $CKAN_HOME/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini

# create log files directories
RUN mkdir /var/log/ckan

# Install CKAN Datapusher
RUN virtualenv $CKAN_DATAPUSHER_HOME
RUN $CKAN_DATAPUSHER_HOME/bin/pip install \
      -e git+https://github.com/ckan/datapusher.git#egg=datapusher && \
    $CKAN_DATAPUSHER_HOME/bin/pip install \
      -r $CKAN_DATAPUSHER_HOME/src/datapusher/requirements.txt

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

# Disable SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh
