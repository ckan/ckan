#!/bin/sh

echo "*** Running linkWho ***"
#ln -s /home/ubuntu/src/ckan/who.ini /etc/ckan/default/who.ini
ls -ltr /usr/lib/ckan/default/src/ckan/who.ini
ls -ltr /etc/ckan/default/who.ini

ln -s /usr/lib/ckan/default/src/ckan/who.ini /etc/ckan/default/who.ini

ls -ltr /usr/lib/ckan/default/src/ckan/who.ini
ls -ltr /etc/ckan/default