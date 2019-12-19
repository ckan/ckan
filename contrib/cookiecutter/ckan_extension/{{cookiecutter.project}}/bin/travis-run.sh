#!/bin/sh -e
set -ex

flake8 --version
# stop the build if there are Python syntax errors or undefined names
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics --exclude ckan,{{ cookiecutter.project }}

pytest --ckan-ini=subdir/test.ini \
          --cov=ckanext.{{ cookiecutter.project_shortname }}

# strict linting
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics --exclude ckan,{{ cookiecutter.project }}
