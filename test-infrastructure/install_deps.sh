#!/bin/sh

set -e

# OS Dependencies
apt update
apt install -y postgresql-client
## MaxOS  ``brew install postgresql libmagic``

#Python Dependencies
pip install -U pip
pip install -U setuptools
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -e .
pip check
