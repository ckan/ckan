#!/bin/bash

if [[ $1 == "-h" || $1 == "--help" ]]; then
    echo "Usage: backup_ckan_volumes.sh [LOCAL_BACKUP_PATH] [CKAN_CONTAINER] [TEMP_CONTAINER_IMAGE]"
    echo "Exports CKAN volume contents to separate TAR files"
    echo "  CKAN_CONTAINER default is \"ckan\""
    echo "  LOCAL_BACKUP_PATH default is the current directory"
    echo "  TEMP_CONTAINER_IMAGE default is \"ubuntu\""

    exit
fi

# Root directory in the temporary container to dump CKAN backups into
BACKUP_ROOT="/ckan_backup"

CKAN_HOME_PATH="/usr/lib/ckan/venv/src"
CKAN_CONFIG_PATH="/etc/ckan"
CKAN_STORAGE_PATH="/var/lib/ckan/storage"

LOCAL_BACKUP_PATH=$1
CKAN_CONTAINER=$2
TEMP_CONTAINER_IMAGE=$3

DATESTAMP="`date --utc +\%Y-\%m-\%d`"

# CKAN container name defaults to "ckan"
if [ ! $CKAN_CONTAINER ]; then
	CKAN_CONTAINER="ckan"
    echo "No source container specified, defaulting to \"$CKAN_CONTAINER\""
fi;

# Current directory is assumed if none are specified
if [ ! $LOCAL_BACKUP_PATH ]; then
	LOCAL_BACKUP_PATH=$(pwd)
    echo "No destination path specified, defaulting to $LOCAL_BACKUP_PATH"
else
    LOCAL_BACKUP_PATH=`realpath $LOCAL_BACKUP_PATH`
fi;

# "Ubuntu" is the image for the temporary container if not specified because of
# reasons.  Use what you like.
if [ ! $TEMP_CONTAINER_IMAGE ]; then
	TEMP_CONTAINER_IMAGE="ubuntu"
    echo "No image specified for temporary container, defaulting to \"$TEMP_CONTAINER_IMAGE\""
fi;

# Uses the root directory + a directory with the date to store the backups into
FINAL_BACKUP_DIR="$BACKUP_ROOT/$DATESTAMP"

LOCAL_BACKUP_DIR="$LOCAL_BACKUP_PATH/$DATESTAMP"

mkdir -p $LOCAL_BACKUP_DIR

echo "Current Date/Time: $DATESTAMP"
echo "Attaching to volumes from container: $CKAN_CONTAINER"
echo "Dumping contents to: $LOCAL_BACKUP_PATH"
echo "Internal path to backups: $FINAL_BACKUP_DIR"
echo "Using image: $TEMP_CONTAINER_IMAGE"

echo "docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_home.tar $CKAN_HOME_PATH"
sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_home.tar $CKAN_HOME_PATH

echo "docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_config.tar $CKAN_CONFIG_PATH"
sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_config.tar $CKAN_CONFIG_PATH

echo "docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_storage.tar $CKAN_STORAGE_PATH"
sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar cvf $FINAL_BACKUP_DIR/ckan_storage.tar $CKAN_STORAGE_PATH

echo "Backup Complete."
echo $LOCAL_BACKUP_DIR
ls -lah $LOCAL_BACKUP_DIR
