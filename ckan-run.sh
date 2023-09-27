#!/bin/bash
echo "CKAN DB INIT"
ckan -c /usr/lib/ckan/config/who.ini db init
echo "CKAN RUN"
ckan -c /usr/lib/ckan/config/who.ini run --host 0.0.0.0
