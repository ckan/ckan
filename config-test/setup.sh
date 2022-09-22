#!/bin/sh


docker-compose up -d
docker-compose exec ckan config-test/install_deps.sh
docker-compose exec ckan config-test/init_environment.sh
