#!/bin/sh

# OS Dependencies
apt update
apt install -y postgresql-client

#Python Dependencies
pip install -U pip
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -e .
pip check
