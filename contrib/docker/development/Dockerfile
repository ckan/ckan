FROM phusion/baseimage:0.9.13
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
        postfix \
        build-essential \
        git \
        libxml2-dev \
        libxslt1-dev \
        libgeos-c1 \
        supervisor

# Perpare CKAN directories
RUN mkdir -p $CKAN_CONFIG $CKAN_DATA

# create log files directories
RUN mkdir /var/log/ckan

# Install CKAN Datapusher
RUN virtualenv $CKAN_DATAPUSHER_HOME
RUN $CKAN_DATAPUSHER_HOME/bin/pip install \
      -e git+https://github.com/ckan/datapusher.git#egg=datapusher && \
    $CKAN_DATAPUSHER_HOME/bin/pip install \
      -r $CKAN_DATAPUSHER_HOME/src/datapusher/requirements.txt

# Configure postfix
ADD ./main.cf /etc/postfix/main.cf

# Configure runit
ADD ./my_init.d /etc/my_init.d
ADD ./svc /etc/service
CMD ["/sbin/my_init"]

VOLUME ["/var/lib/ckan", "/usr/lib/ckan/default", "/etc/ckan/default", "/var/log"]
EXPOSE 5000 8800

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
