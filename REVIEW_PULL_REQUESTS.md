# Review CIOOS CKAN Pull Requests

## To Start
we use docker image tags of the form 'PR##' for pull request directly to the
ckan repository or 'repo_name-PR##' for pull request originated in one of the
submodules. for example pull request 40 from ckanext-cioos_theme would be tagged
as 'ckanext-cioos_theme-PR40'

To pull the relevant docker image first examine the comments attached to the pull request.
On newer requests an auto generated comment will indicate the command needed to
pull the relevant image. If no comment exists you can manually find the image
by identify the pull request number and repository name. Then find the matching
image on the docker hub [cioos/ckan](https://hub.docker.com/repository/docker/cioos/ckan)
image repository.

To test using the new image:

### Pull image
sudo docker pull cioos/ckan:ckanext-cioos_theme-PR40
or
sudo CKAN_TAG=ckanext-cioos_theme-PR40 docker-compose pull ckan

### Remove Home Volume and Restart
sudo docker-compose down
sudo docker volume rm docker_ckan_home
sudo docker-compose up -d

If may need to add/remove plugins or config settings from your production.ini.
See the pull request description for details or post a comment to the pull request
if anything is unclear.

## Then it got noodly
What if a pull request depends on changes from another submodule and thus another
pull request?

Let’s use an example. Say you have the following pull request which depend on each other.
https://github.com/cioos-siooc/ckanext-cioos_theme/pull/38
https://github.com/cioos-siooc/ckanext-spatial/pull/11
From the commits as seen in github we can see that the branch name related to these PR's is
`#50_default_minimum_zoom_level_in_dataset_map` in both repos.


In this case the auto generated images fail us and we have to resort to smashing
the code together ourselves. This can be done in two ways.

### Option 1
Here we generate a new image which merges our existing PR's
#### Clone / Checkout the code
Option. If not already done, clone/checkout the github cioos/ckan repo.
```
git clone https://github.com/cioos-siooc/ckan.git
cd ckan
git checkout cioos
```

#### create a new branch on cioos/ckan
```
git branch testPR50
git checkout testPR50
```

#### set the submodules to the appropriate commit/branch
in this case checking out `#50_default_minimum_zoom_level_in_dataset_map` would be sufficient
```
cd ~/ckan/contrib/docker/src/ckanext-cioos_theme
git checkout '#50_default_minimum_zoom_level_in_dataset_map'

cd ~/ckan/contrib/docker/src/ckanext-spatial
git checkout '#50_default_minimum_zoom_level_in_dataset_map'

cd ~/ckan
git status
git add contrib/docker/src/ckanext-cioos_theme
git add contrib/docker/src/ckanext-spatial
git status
git commit

git push --set-upstream origin testPR50
```

#### create a pull request from that branch to the `cioos` branch in GitHub
This can be done via your favourite git application like `gitkraken`, the `github gui`,
or via the command line using `hub pull-request`. Once created it will trigger
the auto image build and a new image will be available to pull down and test as above.
Note if you are using the hub app you may need to generate a personal access
token in GitHub to use as your password.

```
hub pull-request -b cioos -h testPR50 -m "Test fix for Issue 50"
```

### Option 2
This option involves checking out the code base and coping the appropriate code into
a running ckan volume. The steps involved are outlined below.

#### Pull appropriate image
This could be a PR, daily, or latest image.
```
sudo CKAN_TAG=latest docker-compose pull ckan
```

if the docker_ckan_home does not exist we will need to start ckan so that it is created.
```
sudo docker-compose up -d
```

#### Checkout the code
Option. If not already done, checkout the github cioos/ckan repo.
```
git clone https://github.com/cioos-siooc/ckan.git
cd ckan
git checkout cioos
```

#### Update the submodules
Update each submodule that has been changed to the appropriate commit
```
cd ~/ckan/contrib/docker/src/ckanext-cioos_theme
git checkout '#50_default_minimum_zoom_level_in_dataset_map'

cd ~/ckan/contrib/docker/src/ckanext-spatial
git checkout '#50_default_minimum_zoom_level_in_dataset_map'
```

#### Export volume path to environment variable
Optional. you could do it the long way and put in the full path to the volume.
I find it easier to export.
```
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
```
#### Copy code to volumes
```
sudo cp -r src/ckanext-cioos_theme/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-spatial/ $VOL_CKAN_HOME/venv/src/
```

#### Update config as needed
```
sudo nano $VOL_CKAN_CONFIG/production.ini
```

#### (Re)start the containers
in this case just the ckan container
```
sudo docker-compose restart ckan
```
