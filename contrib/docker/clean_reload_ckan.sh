sudo docker-compose rm -f -s ckan
sudo docker-compose rm -f -s ckan_gather_harvester
sudo docker-compose rm -f -s ckan_fetch_harvester
sudo docker-compose rm -f -s ckan_run_harvester
sudo docker volume rm docker_ckan_home
