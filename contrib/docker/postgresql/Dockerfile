FROM phusion/baseimage:0.9.13
MAINTAINER Open Knowledge

# set UTF-8 locale
RUN locale-gen en_US.UTF-8 && \
    echo 'LANG="en_US.UTF-8"' > /etc/default/locale

# Install PostgreSQL and PostGIS
RUN apt-get -qq update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -qq -y postgresql postgresql-contrib postgis postgresql-9.3-postgis-2.1

# Allow connections from anywhere.
RUN sed -i -e"s/^#listen_addresses =.*$/listen_addresses = '*'/" /etc/postgresql/9.3/main/postgresql.conf
RUN echo "host    all    all    0.0.0.0/0    trust" >> /etc/postgresql/9.3/main/pg_hba.conf

EXPOSE 5432
VOLUME  ["/etc/postgresql", "/var/log/postgresql", "/var/lib/postgresql"]
ADD ./svc /etc/service/
CMD ["/sbin/my_init"]
