#!/bin/sh -e
set -ex

flake8 --version
# stop the build if there are Python syntax errors or undefined names
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics --exclude ckan,{{ cookiecutter.project }}

nosetests --ckan \
          --nologcapture \
          --with-pylons=subdir/test.ini \
          --with-coverage \
          --cover-package=ckanext.{{ cookiecutter.project_shortname }} \
          --cover-inclusive \
          --cover-erase \
          --cover-tests

# strict linting
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics --exclude ckan,{{ cookiecutter.project }}
