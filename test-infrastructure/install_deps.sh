#!/bin/sh

# OS Dependencies
apt update
apt install -y postgresql-client

#Python Dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt
python setup.py develop
pip check
