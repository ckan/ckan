#!/bin/sh

set -e

# OS Dependencies
apt-get update
apt-get install -y postgresql-client
## MacOS  ``brew install postgresql libmagic``

#Python Dependencies
pip install -U pip
pip install -U setuptools
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -e .
pip check
