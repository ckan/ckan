sudo docker-compose stop ckan
sudo docker-compose stop ckan_gather_harvester
sudo docker-compose stop ckan_fetch_harvester
sudo docker-compose stop ckan_run_harvester
sudo docker-compose rm -f ckan
sudo docker-compose rm -f ckan_gather_harvester
sudo docker-compose rm -f ckan_fetch_harvester
sudo docker-compose rm -f ckan_run_harvester
docker volume rm docker_ckan_home
