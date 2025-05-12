#!/bin/sh
# Update docker-compose.yml command from /srv/app/bin/serve.sh to
# command:
#      ['tail', '-f', '/etc/debian_version']
# so the conotainer boots but does not run
# then run setup.sh, create-test-data.sh then this file
docker compose exec ckan  ckan -c ckan.ini run -H 0.0.0.0

