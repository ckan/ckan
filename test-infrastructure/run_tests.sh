#!/bin/sh

mkdir -p ~/junit/result


python -m pytest $PYTEST_COMMON_OPTIONS

# use run_tests_split.sh to split work across containers and run tests in parallel like GitHub Actions use commands like:
# note that this requires multiple database/solr instances to run without data race collisions.
#python -m pytest $PYTEST_COMMON_OPTIONS --splits 2 --group 1 --splitting-algorithm least_duration &
#python -m pytest $PYTEST_COMMON_OPTIONS --splits 2 --group 2 --splitting-algorithm least_duration
