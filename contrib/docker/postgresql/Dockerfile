FROM postgres:9.6
MAINTAINER Open Knowledge

# Allow connections; we don't map out any ports so only linked docker containers can connect
RUN echo "host all  all    0.0.0.0/0  md5" >> /var/lib/postgresql/data/pg_hba.conf

# Customize default user/pass/db
ENV POSTGRES_USER ckan
ENV POSTGRES_PASSWORD ckan
ENV POSTGRES_DB ckan
