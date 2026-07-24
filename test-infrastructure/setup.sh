#!/bin/sh


docker compose up -d
docker compose exec ckan test-infrastructure/install_deps.sh
docker compose exec ckan test-infrastructure/init_environment.sh
