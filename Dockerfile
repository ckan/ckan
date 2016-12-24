FROM phusion/baseimage:0.9.15
MAINTAINER Open Knowledge

# Disable SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

ENV HOME /root
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CKAN_DATA /var/lib/ckan

# Install required packages
RUN apt-get -q -y update && \
    DEBIAN_FRONTEND=noninteractive apt-get -q -y install \
        python-minimal \
        python-dev \
        python-virtualenv \
        libpq-dev \
        nginx-light \
        postfix \
        build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install CKAN
RUN virtualenv $CKAN_HOME
RUN mkdir -p $CKAN_HOME $CKAN_CONFIG $CKAN_DATA
RUN chown www-data:www-data $CKAN_DATA

RUN $CKAN_HOME/bin/pip install gunicorn==19.1.0 gevent==1.0.1
ADD ./requirements.txt $CKAN_HOME/src/ckan/requirements.txt
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
ADD . $CKAN_HOME/src/ckan/
RUN $CKAN_HOME/bin/pip install -e $CKAN_HOME/src/ckan/
RUN ln -s $CKAN_HOME/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini

# Configure nginx
ADD ./contrib/docker/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /var/cache/nginx

# Configure postfix
ADD ./contrib/docker/main.cf /etc/postfix/main.cf

# Configure runit
ADD ./contrib/docker/my_init.d /etc/my_init.d
ADD ./contrib/docker/svc /etc/service
CMD ["/sbin/my_init"]

# Volumes
VOLUME ["/etc/ckan/default"]
VOLUME ["/var/lib/ckan"]
EXPOSE 80

RUN rm -rf /tmp/* /var/tmp/*
