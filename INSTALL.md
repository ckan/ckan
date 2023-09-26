python -m venv /workspace/ckan/ckan/default
. /workspace/ckan/ckan/default/bin/activate
pip install -r requirements.txt
python setup.py install
set -o allexport
source .env.development
ckan -c test-core.ini db init
ckan -c test-core.ini run