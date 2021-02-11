# Review CIOOS CKAN Pull Requests

## To Start
we use docker image tags of the form 'PR##' for pull request directly to the ckan repository or 'repot_name-PR##' for pull request orignated in one of the submodules. for example pull request 40 from ckanext-cioos_theme would be taged as 'ckanext-cioos_theme-PR40'

To pull the relevent docker image first examine the comments od the pull request. On newer requests an auto generated comment will indicate the command needed to pull the relavent image. If no comment exists you can manuually find the image by identify the pull request number and repository name. Then find the matching image on the docker hub [cioos/ckan](https://hub.docker.com/repository/docker/cioos/ckan) image repository.

To test using the new image:

### Pull image
sudo docker pull cioos/ckan:ckanext-cioos_theme-PR40
or
sudo CKAN_TAG=ckanext-cioos_theme-PR40 docker-compose pull ckan

### Remove Home Volume and Restart
sudo docker-compose down
sudo docker volume rm docker_ckan_home
sudo docker-compose up -d

If may need to add/remove plugins or config settings from your production.ini. See the pull request description for details or post a comment to the pull request if anything is unclear.

## then it got noodle
What if a pull request depends on changes from another submodule and thus another pull request?

TBD
