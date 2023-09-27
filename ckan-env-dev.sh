#!/bin/bash
echo "....crea el entorno virtual"
python -m venv /workspace/ckan/ckan/default
. /workspace/ckan/ckan/default/bin/activate
echo "....instala y buildea ckan"
pip install -r requirements.txt
python setup.py install