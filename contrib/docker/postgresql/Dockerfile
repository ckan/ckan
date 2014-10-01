FROM postgres:9.3.5

RUN apt-get update && apt-get install -y postgis

EXPOSE 5432

VOLUME  ["/etc/postgresql", "/var/log/postgresql", "/var/lib/postgresql"]
