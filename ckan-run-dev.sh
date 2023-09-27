#!/bin/bash
echo "....crea el entorno virtual"
python -m venv /workspace/ckan/ckan/default
. /workspace/ckan/ckan/default/bin/activate
echo "....instala y buildea ckan"
pip install -r requirements.txt
python setup.py install
echo "....carga variables de entorno"
#set -o allexport
#source .env.development
echo "....ejecuta migraciones"
ckan -c test-core.ini db init
echo "....ckan run"
ckan -c test-core.ini run