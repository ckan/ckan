FROM phusion/baseimage:0.9.10
MAINTAINER Open Knowledge Foundation

# Disable SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

ENV HOME /root
ENV CKAN_HOME /usr/lib/ckan

# Install required packages
RUN apt-get -q -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get -q -y install \
        python-minimal \
        python-dev \
        python-virtualenv \
        libevent-dev \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        nginx-light \
        postfix \
        build-essential

# Install CKAN
RUN virtualenv $CKAN_HOME
RUN mkdir -p $CKAN_HOME /etc/ckan /var/lib/ckan

RUN $CKAN_HOME/bin/pip install gunicorn==18.0 gevent==1.0.1
ADD ./requirements.txt $CKAN_HOME/src/ckan/requirements.txt
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
ADD . $CKAN_HOME/src/ckan/
RUN $CKAN_HOME/bin/pip install -e $CKAN_HOME/src/ckan/
RUN ln -s $CKAN_HOME/src/ckan/ckan/config/who.ini /etc/ckan/who.ini

# Configure nginx
ADD ./contrib/docker/nginx.conf /etc/nginx/nginx.conf

# Configure postfix
ADD ./contrib/docker/main.cf /etc/postfix/main.cf

# Configure runit
ADD ./contrib/docker/svc /etc/service
CMD ["/sbin/my_init"]

VOLUME ["/var/lib/ckan"]
EXPOSE 80

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
