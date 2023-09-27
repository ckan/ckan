#/bin/bash
echo "Ejecución de migraciones"
ckan -c /usr/lib/who.ini db init

echo "CKAN RUN"
ckan -c /usr/lib/who.ini run