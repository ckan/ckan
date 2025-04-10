#!/bin/sh
set -ex

# This script will merge test results if junit.xml does not exist or if coverage-data folder exists

JUNIT_RESULTS_DIR="${JUNIT_RESULTS_DIR:-./junit/result}"
COVERAGE_DATA_DIR="${COVERAGE_DATA_DIR:-./overage-data}"

if [ ! -f ${JUNIT_RESULTS_DIR}/junit.xml ]; then

  echo "not in single run mode, must combine test source results"

  echo "::group::junitparser-merge"
  junitparser merge ${JUNIT_RESULTS_DIR}/*.xml ./junit.xml
  rm ${JUNIT_RESULTS_DIR}/*.xml
  mv ./junit.xml ${JUNIT_RESULTS_DIR}/junit.xml
  echo "::endgroup::"

fi

if [ -d ${COVERAGE_DATA_DIR} ]; then
  echo "::group::coverage combine"
  echo "merge pytest coverage results"
  coverage combine --keep -a ./${COVERAGE_DATA_DIR}/*
  echo "::endgroup::"
fi

mkdir -p results

echo "::group::junit2html generate"
junit2html ${JUNIT_RESULTS_DIR}/junit.xml results/pytest-results.html
cp ${JUNIT_RESULTS_DIR}/junit.xml results/junit_results.xml
echo "::endgroup::"

echo "::group::pytest-html-report"
coverage html -d results/coverage_html
echo "::endgroup::"
