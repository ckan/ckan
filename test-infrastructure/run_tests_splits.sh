#!/bin/sh
set -ex
# Required ARGS:
# * SPLIT_COUNT, how many splits are we wanting, i.e. SPLIT_COUNT=2
# * SPLIT_GROUP, which test group are we in, i.e. SPLIT_GROUP=2
# * PYTEST_COMMON_OPTIONS
#          PYTEST_COMMON_OPTIONS="-v --ckan-ini=test-core-github-actions.ini --cov=ckan --cov=ckanext --cov-branch --cov-report=term-missing  --junitxml=./junit/result/junit-$SPLIT_GROUP.xml  -o junit_family=legacy" -k 'not test_building_the_docs'
#          We usually ignore test 'test_building_the_docs' as its looked after by the docs.yml workflow which provides the sphinx documentation build artifact and it also takes 50 seconds to run


# When running pytest, we write the new test durations using options
# `--store-durations --clean-durations`.
# Option `--clean-durations` is undocumented but you can check its implementation here:
# https://github.com/jerry-git/pytest-split/blob/fb9af7e0122c18a96a7c01ca734c4ab01027f8d9/src/pytest_split/plugin.py#L68-L76
# > Removes the test duration info for tests which are not present while running the suite with
# > '--store-durations'.

echo `pwd`

mkdir -p ./junit/result
echo "$SPLIT_GROUP of $SPLIT_COUNT"

echo "::group::test_durations_fallback_if_required"
if [ ! -f .test_durations ]; then
  echo "unzip pytest test duration details"
  gunzip .test_durations.gz
fi
echo "::endgroup::"

echo "::group::pytest"
pytest $PYTEST_COMMON_OPTIONS --splits $SPLIT_COUNT --group $SPLIT_GROUP --splitting-algorithm least_duration -k 'not test_building_the_docs'
echo "::endgroup::"
