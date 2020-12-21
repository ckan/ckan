.. include:: /_substitutions.rst

===================================
Installing CKAN with Docker Compose
===================================

These instructions are experimental and not meant for production. They are enough to test Ckan, but more stable
and usable instructions for the newest version of CKAN are still missing.

0. Make sure you have docker and docker-compose installed

1. Create your env-file, in particular, take care of the host
  Copy ``contrib/docker/.env.template`` to ``contrib/docker/.env`` and follow instructions

2. build and start  `` docker-compose up --build ``

3. Create superuser account
``docker exec -it ckan ckan -c /etc/ckan/production.ini sysadmin add seanh email=seanh@localhost name=seanh  ``



