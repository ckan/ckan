#!/usr/bin/env bash
set -e;

# Install system packages
sudo apt-get update;
sudo apt-get install git-core -y;
sudo apt-get install python-dev python-pip python-virtualenv -y;
sudo apt-get install postgresql libpq-dev -y;
sudo apt-get install solr-jetty openjdk-8-jdk -y;
sudo apt-get install redis-server -y;
