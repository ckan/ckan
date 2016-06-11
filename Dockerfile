FROM phusion/baseimage:0.9.18
MAINTAINER Open Knowledge

# Environment
ENV CKAN_HOME /usr/lib/ckan/default
ENV CKAN_CONFIG /etc/ckan/default
ENV CKAN_DATA /var/lib/ckan
ENV CKAN_GIT_BRANCH release-v2.5.2

# Install required packages
RUN apt-get -q=2 -y update && DEBIAN_FRONTEND=noninteractive apt-get -q=2 -y install \
        python-dev \
        python-pip \
        python-virtualenv \
        libpq-dev \
        apache2 \
        libapache2-mod-wsgi \
        nginx \
        postfix \
        && apt-get -q=2 -y clean
        
# Install Virtual Environment
RUN mkdir -p $CKAN_HOME/src/ $CKAN_CONFIG $CKAN_DATA
RUN virtualenv --no-site-packages $CKAN_HOME
RUN chown www-data:www-data $CKAN_DATA

# Download CKAN
ADD https://codeload.github.com/ckan/ckan/tar.gz/$CKAN_GIT_BRANCH $CKAN_HOME/ckan-git.tar.gz
RUN tar -zxvf $CKAN_HOME/ckan-git.tar.gz -C $CKAN_HOME/src/
RUN mv $CKAN_HOME/src/ckan-$CKAN_GIT_BRANCH/ $CKAN_HOME/src/ckan/

# Install CKAN
RUN $CKAN_HOME/bin/pip install -r $CKAN_HOME/src/ckan/requirements.txt
RUN $CKAN_HOME/bin/pip install -e $CKAN_HOME/src/ckan/
RUN ln -s $CKAN_HOME/src/ckan/ckan/config/who.ini $CKAN_CONFIG/who.ini

# Configure apache
COPY ./contrib/docker/apache.wsgi $CKAN_CONFIG/apache.wsgi
COPY ./contrib/docker/apache.conf /etc/apache2/sites-available/ckan_default.conf
RUN echo "Listen 8080" > /etc/apache2/ports.conf
RUN a2ensite ckan_default
RUN a2dissite 000-default

# Configure nginx
COPY ./contrib/docker/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /var/cache/nginx

# Configure postfix
COPY ./contrib/docker/main.cf /etc/postfix/main.cf

# Configure runit
COPY ./contrib/docker/my_init.d /etc/my_init.d
COPY ./contrib/docker/svc /etc/service
CMD ["/sbin/my_init"]

# Volumes
VOLUME ["/etc/ckan/default"]
VOLUME ["/var/lib/ckan"]
EXPOSE 80