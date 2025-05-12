#!/bin/sh

#docker compose exec ckan  pytest -v -s --ckan-ini=test-core-ci.ini ckan/tests/lib/test_base.py::test_cache_control_while_logged_in
docker compose exec ckan  pytest -v -s --ckan-ini=test-core-ci.ini
