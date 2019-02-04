#!/bin/sh

echo "*** Running installSolr ***"

wget http://apache.miloslavbrada.cz/lucene/solr/6.6.5/solr-6.6.5.zip && unzip solr-6.6.5.zip
sudo /home/ubuntu/solr-6.6.5/bin/install_solr_service.sh /home/ubuntu/solr-6.6.5.zip > sample.txt &
wait $!
cat sample.txt


sudo -H -u solr bash -c '/opt/solr/bin/solr create -c ckan'
echo "*** mangos ***"
sudo -H -u solr bash -c 'cp /home/ubuntu/resources/solrconfig.xml /var/solr/data/ckan/conf/solrconfig.xml'
sudo -H -u solr bash -c 'rm /var/solr/data/ckan/conf/managed-schema'
sudo -H -u solr bash -c 'cp /home/ubuntu/resources/schema.xml /var/solr/data/ckan/conf/schema.xml'
echo "*** mangos ***"
sudo -H -u solr bash -c 'cat /var/solr/data/ckan/conf/schema.xml'
sudo -H -u solr bash -c 'cat /var/solr/data/ckan/conf/solrconfig.xml'
echo "*** mangos ***"
sudo /etc/init.d/solr restart

