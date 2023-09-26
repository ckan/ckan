python -m venv /workspace/ckan/ckan/default
. /workspace/ckan/ckan/defualt/bin/activate
pip install -r requirements.txt
python setup.py install
set -o allexport
source .env.development
ckan -c development.ini db init
ckan -c development.ini run