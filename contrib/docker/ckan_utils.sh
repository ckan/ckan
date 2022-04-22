#!/bin/bash

# CKAN utility functions and environment variables
# To get started, source this file and then run ckan_list_utils

export CKAN_DOCKER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export CKAN_BASE=$(readlink -f ${CKAN_DOCKER}/../../)
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_STORAGE=`sudo docker volume inspect docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`

ckan_utils_ls() {
    declare -F | grep "ckan_"
    echo "Run 'type <function name>' for more details about each utility function listed above."
}

ckan_variables() {
    echo "CKAN_BASE $CKAN_BASE"
    echo "CKAN_DOCKER: $CKAN_DOCKER"
    echo "VOL_CKAN_HOME: $VOL_CKAN_HOME"
    echo "VOL_CKAN_CONFIG: $VOL_CKAN_CONFIG"
    echo "VOL_CKAN_STORAGE: $VOL_CKAN_STORAGE"
}

ckan_ps() {
    pushd $CKAN_DOCKER
    docker-compose ps
    popd
}

ckan_logs() {
    sudo docker logs ckan
}

ckan_stop() {
    pushd $CKAN_DOCKER
    sudo docker-compose stop ckan
    sudo docker-compose stop ckan_gather_harvester
    sudo docker-compose stop ckan_fetch_harvester
    sudo docker-compose stop ckan_run_harvester
    popd
}

ckan_start() {
    pushd $CKAN_DOCKER
    sudo docker-compose start ckan
    sudo docker-compose start ckan_gather_harvester
    sudo docker-compose start ckan_fetch_harvester
    sudo docker-compose start ckan_run_harvester
    popd
}

ckan_down() {
    pushd $CKAN_DOCKER
    sudo docker-compose down "$@"
    popd
}

ckan_up() {
    pushd $CKAN_DOCKER
    sudo docker-compose up "$@"
    popd
}

ckan_perms() {
    sudo chown 900:900 -R $VOL_CKAN_HOME/venv/src/
}

ckan_reload() {
    bash $CKAN_BASE/ckan_reload_ckan.sh
}

ckan_reindex() {
    sudo docker exec -it ckan -c /etc/ckan/production.ini search-index rebuild
}

ckan_create_admin() {
    sudo docker exec -i ckan -c /etc/ckan/production.ini sysadmin add admin
}

ckan_upgrade() {
    cd $CKAN_DOCKER
    sudo docker-compose down
    # use down -v to remove all volumes in addition to containers
    git pull
    sudo docker-compose pull
    sudo docker-compose up -d --build
}

ckan_compile_css(){
  cd $CKAN_DOCKER/src/ckanext-cioos_theme/ckanext/cioos_theme/public/
  sass --update --style=compressed cioos_atlantic.scss:cioos_atlantic.css cioos_theme.scss:cioos_theme.css
  cd $CKAN_DOCKER
}

ckan_api_setup() {
    echo "Setting up the URL, API_KEY, and conda environment for use with the CKAN API."
    echo "For more information, see:"
    echo "https://github.com/ckan/ckanapi"
    echo "https://docs.ckan.org/en/latest/api/index.html"
    echo ""
    if ! command -v conda &> /dev/null; then
        echo "The conda command is not in the current PATH"
        echo "Typically found at $HOME/miniconda3/etc/profile.d/conda.sh"
        echo "Please enter the full path to your conda.sh"
        read -p CONDA_SH
        export CONDA_SH=$CONDA_SH
    fi
    if ! command -v ckanapi &> /dev/null; then
        echo "The ckanapi command is not in the current PATH"
        echo "Which conda environment enables the ckanapi command?"
        read -p CONDA_ENV
    fi
    if [ -z $CKAN_URL ]; then
        echo "What is the CKAN URL?"
        read -p CKAN_URL
        export CKAN_URL=$CKAN_URL
    fi
    if [ -z $CKAN_API_KEY ]; then
        echo "What is the API key to use?"
        read -p CKAN_API_KEY
        export CKAN_API_KEY=$CKAN_API_KEY
    fi
    echo "a"
}

ckan_api() {
    if [[ -z $CONDA_SH ]] || [[ -z $CONDA_ENV ]] || [[ -z $CKAN_URL ]] || [[ -z $CKAN_API_KEY ]]; then
        echo "A required environment variable for the CKAN API setup is not set."
        echo "Run the ckan_api_setup command to set these first."
    else
        source $CONDA_SH
        conda activate $CONDA_ENV
        ckanapi -r $CKAN_URL -a $CKAN_API_KEY "$@"
    fi
}
