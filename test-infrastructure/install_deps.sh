#!/bin/sh

set -e

# OS Dependencies
apt-get update
apt-get install -y postgresql-client
## MacOS  ``brew install postgresql libmagic``

#Python Dependencies
pip install -U pip
pip install -U setuptools
pip install -r requirements.txt -r dev-requirements.txt -e .
pip check
