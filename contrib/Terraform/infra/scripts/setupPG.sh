#!/bin/sh

echo "**** running setupPG.sh ****"

#if [ -z "$1" ]
#  then
#    echo "No argument supplied, taking the listner as localhost"
#fi
# make ckanpassword as variable

# sudo -u postgres psql -l
sudo -u postgres createuser -S -D -R ckan_default
sudo -u postgres psql -c "ALTER USER ckan_default PASSWORD 'ckanpassword';"
sudo -u postgres createdb -O ckan_default ckan_default -E utf-8
sudo -u postgres psql -l > sample.txt &
wait $!
cat sample.txt
