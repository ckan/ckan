#!/bin/bash
echo "....ejecuta migraciones"
ckan -c test-core.ini db init
echo "....ckan run"
ckan -c test-core.ini run